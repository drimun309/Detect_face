"""Convert ceh1_roi_analytics.md to PDF via HTML + headless Chrome/Edge."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MD = ROOT / "ceh1_roi_analytics.md"
HTML = ROOT / "ceh1_roi_analytics.html"
PDF = ROOT / "ceh1_roi_analytics.pdf"

BROWSERS = [
    Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
    Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
    Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
]


def inline_md(text: str) -> str:
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"\*(.+?)\*", r"<em>\1</em>", text)
    return text


def md_to_html(md: str) -> str:
    lines = md.splitlines()
    out: list[str] = []
    in_table = False
    table_header_done = False
    list_mode: str | None = None

    def close_list() -> None:
        nonlocal list_mode
        if list_mode:
            out.append("</ul>" if list_mode == "ul" else "</ol>")
            list_mode = None

    for line in lines:
        stripped = line.strip()

        if stripped.startswith("|"):
            close_list()
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            if all(set(c) <= {"-", ":"} for c in cells):
                continue
            if not in_table:
                out.append("<table>")
                in_table = True
                table_header_done = False
            tag = "th" if not table_header_done else "td"
            row = "".join(f"<{tag}>{inline_md(c)}</{tag}>" for c in cells)
            out.append(f"<tr>{row}</tr>")
            if tag == "th":
                table_header_done = True
            continue

        if in_table:
            out.append("</table>")
            in_table = False
            table_header_done = False

        if stripped == "---":
            close_list()
            out.append("<hr>")
        elif stripped.startswith("# "):
            close_list()
            out.append(f"<h1>{inline_md(stripped[2:])}</h1>")
        elif stripped.startswith("## "):
            close_list()
            out.append(f"<h2>{inline_md(stripped[3:])}</h2>")
        elif stripped.startswith("### "):
            close_list()
            out.append(f"<h3>{inline_md(stripped[4:])}</h3>")
        elif re.match(r"^\d+\.\s", stripped):
            if list_mode != "ol":
                close_list()
                out.append("<ol>")
                list_mode = "ol"
            item = re.sub(r"^\d+\.\s", "", stripped)
            out.append(f"<li>{inline_md(item)}</li>")
        elif stripped.startswith("- "):
            if list_mode != "ul":
                close_list()
                out.append("<ul>")
                list_mode = "ul"
            out.append(f"<li>{inline_md(stripped[2:])}</li>")
        elif stripped == "":
            close_list()
            continue
        else:
            close_list()
            out.append(f"<p>{inline_md(stripped)}</p>")

    if in_table:
        out.append("</table>")
    close_list()

    body = "\n".join(out)
    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <title>Аналитический отчёт: цех 1</title>
  <style>
    @page {{ margin: 14mm 12mm; }}
    body {{
      font-family: "Segoe UI", Arial, sans-serif;
      font-size: 10pt;
      line-height: 1.4;
      color: #1a1a1a;
      margin: 0 auto;
    }}
    h1 {{ font-size: 18pt; margin: 0 0 8px; color: #0f2d52; }}
    h2 {{
      font-size: 12pt;
      margin: 18px 0 8px;
      color: #0f2d52;
      border-bottom: 1px solid #d0d7de;
      padding-bottom: 3px;
    }}
    h3 {{ font-size: 10.5pt; margin: 12px 0 6px; color: #333; }}
    p {{ margin: 5px 0; }}
    hr {{ border: none; border-top: 1px solid #d0d7de; margin: 12px 0; }}
    ul, ol {{ margin: 5px 0 8px 18px; padding: 0; }}
    li {{ margin: 3px 0; }}
    table {{
      width: 100%;
      border-collapse: collapse;
      margin: 8px 0 12px;
      font-size: 8.5pt;
      table-layout: fixed;
      word-wrap: break-word;
    }}
    th, td {{
      border: 1px solid #c9d1d9;
      padding: 4px 5px;
      text-align: left;
      vertical-align: top;
    }}
    th {{ background: #f0f4f8; font-weight: 600; }}
    strong {{ color: #0f2d52; }}
  </style>
</head>
<body>
{body}
</body>
</html>
"""


def find_browser() -> Path:
    for path in BROWSERS:
        if path.is_file():
            return path
    raise FileNotFoundError("Chrome или Edge не найден")


def main() -> None:
    md = MD.read_text(encoding="utf-8")
    HTML.write_text(md_to_html(md), encoding="utf-8")
    browser = find_browser()
    cmd = [
        str(browser),
        "--headless=new",
        "--disable-gpu",
        "--no-sandbox",
        f"--print-to-pdf={PDF}",
        HTML.as_uri(),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0 or not PDF.is_file():
        print(result.stderr or result.stdout, file=sys.stderr)
        raise SystemExit(f"Не удалось создать PDF (код {result.returncode})")
    print(PDF)


if __name__ == "__main__":
    main()
