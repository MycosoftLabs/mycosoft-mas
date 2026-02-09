import pathlib
W=pathlib.Path(r"C:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website")
a=W/"app"/"natureos"/"ai-studio"/"page.tsx"
t=a.read_text(encoding="utf-8")
old='command.includes("show workflows")) {'
new='command.includes("show workflows") || command.includes("show pipeline") || command.includes("show system status") || command.includes("open activity")) {'
if old in t:
    a.write_text(t.replace(old,new,1),encoding="utf-8")
    print("OK voice patched")
elif "show pipeline" in t:
    print("Already patched")
else:
    print("WARN line not found")