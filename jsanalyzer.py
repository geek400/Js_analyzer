import os
import re
import jsbeautifier
import httpx
import argparse
import asyncio
import google.generativeai as genai
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor, as_completed

# ====== Load ENV + Gemini Setup ======
load_dotenv()
GEMINI_API_KEY = os.getenv("API_KEY")
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.5-flash')

# ====== Async Get Content from URL or File ======
async def get_js_content(path):
    try:
        if path.startswith("http"):
            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.get(path)
                return path, r.text if r.status_code == 200 else f"[ERROR] HTTP {r.status_code}"
        elif os.path.exists(path):
            return path, open(path, "r", encoding="utf-8").read()
        else:
            return path, "[ERROR] Invalid path"
    except Exception as e:
        return path, f"[ERROR] {e}"

# ====== Async Gather Wrapper ======
async def gather_all(paths):
    tasks = [get_js_content(p) for p in paths]
    return await asyncio.gather(*tasks)

# ====== Beautify Code ======
def beautify_js(code):
    return jsbeautifier.beautify(code)

# ====== Explain Code with Gemini ======
def explain_with_gemini(code):
    prompt = f"""
    Analyze this JavaScript code and explain in detail:
    - Any secrets, hardcoded API keys, suspicious logic?
    - Any security risks like eval, setTimeout with string, or tokens?

    JS Code:
    {code}
    """
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return f"[ERROR] Gemini failed: {e}"

# ====== Batch-style Wrapper ======
def batch_explain_with_gemini(beautified_list, max_workers=3, verbose=False):
    results = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(explain_with_gemini, code): idx for idx, code in enumerate(beautified_list)}
        for future in as_completed(futures):
            idx = futures[future]
            try:
                result = future.result()
            except Exception as e:
                result = f"[ERROR] Gemini failed: {e}"
            results.append((idx, result))
            if verbose:
                print(f"[+] Finished explanation for file #{idx + 1}")
    results.sort()
    return [res for _, res in results]

# ====== Extract Info ======
def extract_info(code):
    urls = re.findall(r'https?://[^\s\'"]+', code)
    tokens = re.findall(r'(?:api[_-]?key|token|secret)[\s=:]+["\']?([\w-]{8,})', code, re.IGNORECASE)
    return {
        "urls": list(set(urls)),
        "tokens": list(set(tokens))
    }

# ====== Save Markdown Output ======
def save_output(name, explanation, extracted, out_dir="output"):
    os.makedirs(out_dir, exist_ok=True)
    md_path = os.path.join(out_dir, f"{name}.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("## AI Explanation\n" + explanation + "\n")
        f.write("\n## Extracted URLs:\n" + "\n".join(extracted["urls"]) + "\n")
        f.write("\n## Extracted Tokens:\n" + "\n".join(extracted["tokens"]) + "\n")

# ====== Main Driver ======
def main():
    parser = argparse.ArgumentParser(
        description=" AI-based JavaScript analyzer using Gemini",
        epilog="Example:\n  python tool.py -i js_list.txt -v -t 5",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument("-i", "--input", required=True, help="Input file containing JS paths/URLs")
    parser.add_argument("-v", "--verbose", action="store_true", help="Increase output verbosity")
    parser.add_argument("-t", "--thread", type=int, default=3, help="Number of threads (default=3, max=10)")
    parser.add_argument("-q", "--quiet", action="store_true", help="Suppress all non-error output")

    args = parser.parse_args()

    # Clamp threads between 1 and 10
    max_workers = max(1, min(args.thread, 10))

    if not os.path.exists(args.input):
        print("[ERROR] Input file not found.")
        return

    with open(args.input) as f:
        paths = [line.strip() for line in f if line.strip()]

    if not paths:
        print(" [ERROR] No JS paths/URLs found in input file.")
        return

    # ==== Use Async to Fetch All Content Fast ====
    raw_results = asyncio.run(gather_all(paths))

    valid_js = [(path, content) for path, content in raw_results if not content.startswith("[ERROR]")]
    errored = [(path, content) for path, content in raw_results if content.startswith("[ERROR]")]

    if not args.quiet:
        for path, error in errored:
            print(f"[!] Skipped {path}: {error}")

    if not valid_js:
        print(" No valid JS files found.")
        return

    beautified_codes = [beautify_js(code) for _, code in valid_js]

    if not args.quiet:
        print(f"Sending {len(beautified_codes)} files to Gemini in batch with {max_workers} threads...")
        print("This process may take some time...")

    explanations = batch_explain_with_gemini(beautified_codes, max_workers=max_workers, verbose=args.verbose)

    for i, (path, code) in enumerate(valid_js):
        base = os.path.basename(path).split("?")[0]
        name = re.sub(r'[\\/*?:"<>|]', "_", base.replace(".js", ""))
        extracted = extract_info(code)
        save_output(name, explanations[i], extracted)

        if args.verbose and not args.quiet:
            print(f"[✓] Saved: output/{name}.md")

    if not args.quiet:
        print("\n Done! All output saved in 'output/' folder.")

# ====== Entry Point ======
if __name__ == "__main__":
    main()
