# Publish this coursework repository to GitHub

Account: **garyWang2026**. Suggested repository name: **ftec5660-simplemem-reproduction**.

This guide publishes the existing local Git repository and preserves its commits. The repository has not been published by the preparation process. The suggested URL below is a target, not a verified live repository.

## Recommended: GitHub Desktop

1. Install [GitHub Desktop](https://desktop.github.com/) for your Mac and sign in as `garyWang2026`.
2. Select **File > Add Local Repository > Choose**. Choose `/Users/garywen/Desktop/CUHK/FTEC5660/project02/SimpleMem`, then **Add Repository**. Select the SimpleMem folder itself, not its parent or the downloaded ZIP. Do not create a second repository.
3. Review the existing **History** tab. The preparation has already committed the materials locally. The current branch is `reproduction`; retaining that branch is fine.
4. Click **Publish repository**. Set the name to `ftec5660-simplemem-reproduction`. Suggested description: `FTEC5660 reproduction of SimpleMem with a budgeted LoCoMo reflection ablation.`
5. Choose your personal account (Organization: **None**). For a publicly accessible coursework link, clear **Keep this code private**. If you choose private, grant the instructor access before submission.
6. Click **Publish Repository** and wait for completion. Use **Repository > View on GitHub** to inspect the result.
7. Check that the root coursework banner, `submission/REPORT.md`, the PDF under `output/pdf/`, presentation script, result tables and commit history are visible. Confirm `.env`, root `config.py`, `.venv` and `.cache` are absent. Keep upstream `LICENSE` and attribution.
8. Submit the resulting repository link. If you used the suggested name, its expected form is `https://github.com/garyWang2026/ftec5660-simplemem-reproduction`.

Existing author assets are part of the inherited source tree. Local model weights, API keys, virtual environments and temporary run folders are ignored. Do not drag the entire parent folder or use a new unfiltered ZIP upload.

For later edits, review **Changes**, enter a clear summary, choose **Commit to reproduction**, then **Push origin**. A local commit saves history on your computer; pushing sends it to GitHub. Do not force-push or reset history for this submission.

Official instructions: [add a local repository](https://docs.github.com/en/desktop/adding-and-cloning-repositories/adding-a-repository-from-your-local-computer-to-github-desktop), [publish an existing project](https://docs.github.com/en/desktop/adding-and-cloning-repositories/adding-an-existing-project-to-github-using-github-desktop).

## Optional terminal alternative

On GitHub, create an empty repository in your personal account using the suggested name. Leave the initialization options for README, license and .gitignore unchecked because they already exist locally. Then run:

```sh
cd /Users/garywen/Desktop/CUHK/FTEC5660/project02/SimpleMem
git remote -v
git remote add origin https://github.com/garyWang2026/ftec5660-simplemem-reproduction.git
git push -u origin reproduction
```

These instructions assume no remote is already configured and the remote repository is empty. If you already published using Desktop, do not add another origin. Authenticate using GitHub's supported sign-in/token workflow; do not enter an API key or paste credentials into chat. Do not use your GitHub account password as a Git HTTPS password. The terminal route does not require installing the `gh` command.

## Final course submission

- Add your course-required name/student ID to `submission/REPORT.md` if required. Install the optional PDF dependency with `.venv/bin/python -m pip install -r reproduction/requirements-report.txt`, then regenerate the matching PDF with `.venv/bin/python reproduction/build_report.py`. The prepared report currently identifies only the supplied GitHub handle.
- Upload/submit the report PDF (maximum ten pages; prepared version is seven).
- Submit the published GitHub URL and check that the instructor can open it.
- Record your own Zoom presentation using the English script; keep the recording below 15 minutes. Save/share the recording using the course's accepted method and submit its accessible link. No recording or presentation link has been created by this preparation.
