# Move App Directory - Final Step

## Quick Instructions

The `app/` directory still needs to be moved to the deprecated folder. This requires Administrator privileges due to read-only file permissions.

### Option 1: Run PowerShell Script (Recommended)

1. **Right-click PowerShell** → **Run as Administrator**
2. Navigate to the scripts directory:
   ```powershell
   cd C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas\scripts
   ```
3. Run the script:
   ```powershell
   .\move_app_directory.ps1
   ```

### Option 2: Manual PowerShell Commands

1. **Open PowerShell as Administrator**
2. Navigate to mycosoft-mas root:
   ```powershell
   cd C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas
   ```
3. Remove read-only attributes:
   ```powershell
   Get-ChildItem -Path "app" -Recurse -Force | ForEach-Object {
       $_.Attributes = $_.Attributes -band (-bnot [System.IO.FileAttributes]::ReadOnly)
   }
   ```
4. Move the directory:
   ```powershell
   Move-Item -Path "app" -Destination "_deprecated_mas_website\app" -Force
   ```
5. Verify:
   ```powershell
   Test-Path "app"  # Should return False
   ```

### Option 3: Use Robocopy (Alternative)

```powershell
# Run as Administrator
robocopy "app" "_deprecated_mas_website\app" /E /MOVE /R:5 /W:2 /NP
```

After moving, delete the now-empty `app` directory if it still exists.

---

## After Moving

Once `app/` is moved:
- ✅ Deprecated website files are completely isolated
- ✅ No interference with actual website development
- ✅ Port 3000 is free for the real website
- ✅ Development environment is clean

Next: Follow `docs/MYCOBRAIN_SETUP_INSTRUCTIONS.md` to set up MycoBrain connectivity.
