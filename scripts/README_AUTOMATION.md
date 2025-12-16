# Git Automation Scripts

This directory contains scripts to automate common git workflows, including creating and merging pull requests.

## Setup (One-time)

Run the setup script to configure git identity and GitHub CLI authentication:

```powershell
.\scripts\setup-git-automation.ps1
```

This will:
1. Check/update your git `user.name` and `user.email`
2. Install GitHub CLI if not present
3. Authenticate with GitHub (opens browser)

## Creating and Merging PRs

Use the `create-and-merge-pr.ps1` script to automate the full PR workflow:

```powershell
# Create PR and auto-merge
.\scripts\create-and-merge-pr.ps1 `
    -BranchName "docs/update-readme" `
    -Title "docs: update README" `
    -Body "Updated README with MAS overview" `
    -AutoMerge `
    -DeleteBranch
```

### Parameters

- **BranchName** (required): Name of the branch to create/use
- **Title** (required): PR title
- **Body** (optional): PR description (default: "Automated PR from script")
- **BaseBranch** (optional): Base branch for PR (default: "main")
- **AutoMerge** (switch): Automatically merge the PR after creation
- **DeleteBranch** (switch): Delete the branch after merging (only if AutoMerge is used)

### Examples

**Create PR without merging:**
```powershell
.\scripts\create-and-merge-pr.ps1 `
    -BranchName "feature/new-feature" `
    -Title "Add new feature" `
    -Body "Implements feature X"
```

**Create and auto-merge:**
```powershell
.\scripts\create-and-merge-pr.ps1 `
    -BranchName "fix/bug-fix" `
    -Title "Fix critical bug" `
    -Body "Fixes issue #123" `
    -AutoMerge `
    -DeleteBranch
```

## Manual Workflow

If you prefer to do it manually:

1. **Create branch and commit:**
   ```powershell
   git checkout -b feature/my-feature
   git add .
   git commit -m "Add feature"
   git push -u origin feature/my-feature
   ```

2. **Create PR via GitHub CLI:**
   ```powershell
   gh pr create --base main --head feature/my-feature --title "Add feature" --body "Description"
   ```

3. **Merge PR:**
   ```powershell
   gh pr merge <PR_NUMBER> --merge --delete-branch
   ```

## Troubleshooting

### GitHub CLI not found

If `gh` command is not recognized after installation:
- Restart your terminal/PowerShell session
- Or manually add to PATH: `$env:Path += ";$env:ProgramFiles\GitHub CLI"`

### Authentication required

Run `gh auth login` to authenticate with GitHub. This opens a browser for OAuth.

### Git identity not set

Set globally:
```powershell
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"
```

Or use environment variables per-commit (see script for example).
