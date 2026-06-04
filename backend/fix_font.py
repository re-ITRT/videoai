#!/usr/bin/env python3
path = "/home/ubuntu/video-ai/backend/app/studio/router.py"
with open(path) as f:
    c = f.read()
old = 'force_style=FontName=Serif,FontSize=16,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=1,Outline=1'
new = "force_style='FontName=Serif,FontSize=16,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=1,Outline=1'"
if old in c:
    c = c.replace(old, new)
    with open(path, "w") as f:
        f.write(c)
    print("patched")
else:
    print("not found")
