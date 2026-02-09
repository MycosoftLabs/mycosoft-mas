import pathlib
P=pathlib.Path(__file__).parent
W=pathlib.Path(r"C:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website")
d=W/"app"/"api"/"natureos"/"pipeline-status"
d.mkdir(parents=True,exist_ok=True)
c=""
for x in ["_p1.txt","_p2.txt","_p3.txt"]:
    c+=(P/x).read_text(encoding="utf-8")+"\n"
(d/"route.ts").write_text(c,encoding="utf-8")
print("route.ts",(d/"route.ts").stat().st_size,"bytes")