import pathlib
W=pathlib.Path(r"C:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website")
d=W/"app"/"api"/"natureos"/"pipeline-status"
d.mkdir(parents=True,exist_ok=True)
p1=pathlib.Path(__file__).parent/"_p1.txt"
p2=pathlib.Path(__file__).parent/"_p2.txt"
(d/"route.ts").write_text(p1.read_text(encoding="utf-8"),encoding="utf-8")
print("OK route",(d/"route.ts").stat().st_size,"bytes")
ai=W/"app"/"natureos"/"ai-studio"/"page.tsx"
t=ai.read_text(encoding="utf-8")
o=p2.read_text(encoding="utf-8").strip().split("\n---\n")
if o[0] in t:
    ai.write_text(t.replace(o[0],o[1],1),encoding="utf-8")
    print("OK voice")
elif o[1] in t:
    print("SKIP")
else:
    print("WARN")
