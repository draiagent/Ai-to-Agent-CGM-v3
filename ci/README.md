# CI 工作流

`ci.yml` 是本專案的 GitHub Actions 設定。因為建立此 repo 的權杖沒有 `workflow` scope，
初次推送無法直接放進 `.github/workflows/`。啟用方式擇一：

- 在 GitHub 網頁按 **Add file → Create new file**，路徑填 `.github/workflows/ci.yml`，
  貼上本目錄 `ci.yml` 內容後 commit。
- 或本機執行 `gh auth refresh -h github.com -s workflow`，再
  `git mv ci/ci.yml .github/workflows/ci.yml && git commit && git push`。

工作流內容：`python -m py_compile scripts/*.py`、`unittest`、JSON/Schema 驗證、
範例可重現、密鑰樣式掃描。本機等效檢查：

```bash
python -m unittest discover -s tests -v
```
