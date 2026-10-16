"""Build the offline Hangul Drills PWA from the single-file HTML source.

usage: python build.py ["C:/path/to/Hangul Drills.html"]   (defaults to the copy next to this script)
writes index.html, manifest.webmanifest, sw.js, fonts/ next to this script (icons/ via make_icons.py),
then zips everything for Netlify Drop.
"""
import hashlib, os, re, sys, urllib.request, zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
GROUND = "#f4efe4"; GROUND_DARK = "#15130f"

src = open(sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "Hangul Drills.html"), encoding="utf8").read()

# ---- fonts: localize the Google Fonts stylesheet (hangul itself uses the device's own Korean font) ----
links = re.findall(r'<link rel="stylesheet" href="(https://fonts\.googleapis\.com/css2\?[^"]+)">', src)
assert links, "no Google Fonts link found"
faces = []
os.makedirs(os.path.join(HERE, "fonts"), exist_ok=True)
for href in links:
    css = urllib.request.urlopen(urllib.request.Request(href.replace("&amp;", "&"), headers={"User-Agent": UA})).read().decode()
    for block in re.findall(r"/\* ([\w-]+) \*/\s*(@font-face \{.*?\})", css, re.S):
        subset, face = block
        if subset not in ("latin", "latin-ext"):
            continue
        furl = re.search(r"url\((https://[^)]+)\)", face).group(1)
        name = "fonts/" + hashlib.sha1(furl.encode()).hexdigest()[:12] + ".woff2"
        path = os.path.join(HERE, name)
        if not os.path.exists(path):
            open(path, "wb").write(urllib.request.urlopen(urllib.request.Request(furl, headers={"User-Agent": UA})).read())
        faces.append(face.replace(furl, name))
# Google rotates font URLs, so drop files from earlier builds that nothing points at any more
for f in os.listdir(os.path.join(HERE, "fonts")):
    if not any("fonts/" + f in face for face in faces):
        os.remove(os.path.join(HERE, "fonts", f))
src = re.sub(r'<link rel="preconnect"[^>]*>\s*', "", src)
src = re.sub(r'<link rel="stylesheet" href="https://fonts\.googleapis\.com/[^"]+">', "<style>\n" + "\n".join(faces) + "\n</style>", src)
assert "googleapis" not in src and "gstatic" not in src, "external font reference left over"

# ---- head: app metadata ----
head = f'''<link rel="manifest" href="manifest.webmanifest">
<link rel="icon" href="icons/icon-192.png">
<link rel="apple-touch-icon" href="icons/apple-touch-icon.png">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="Hangul">
<meta name="apple-mobile-web-app-status-bar-style" content="default">
<meta name="theme-color" content="{GROUND}" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="{GROUND_DARK}" media="(prefers-color-scheme: dark)">
'''
src = src.replace("<meta charset=utf8>", "<meta charset=utf-8>", 1).replace("</head>", head + "</head>", 1)

# ---- storage: IndexedDB-backed (localStorage only as a mirror, since it can be blocked) ----
old_store = re.search(r"const store=\{get:k=>\{try\{return localStorage\.getItem\(k\)\}.*?\};\n", src).group(0)
src = src.replace(old_store, "const store=window.KV;\n", 1)
src = src.replace("<script>\n/* ---------------- hangul engine", '<script type="text/plain" id="app">\n/* ---------------- hangul engine', 1)
assert 'id="app"' in src, "app script marker not found"
LOADER = r'''<script>
/* load saved progress from IndexedDB into memory first, then start the app (it reads storage synchronously) */
(function(){
  var MEM=new Map(),db=null,started=false;
  function lsSet(k,v){try{v==null?localStorage.removeItem(k):localStorage.setItem(k,v)}catch(e){}}
  function put(k,v){lsSet(k,v);if(!db)return;try{var os=db.transaction("kv","readwrite").objectStore("kv");v==null?os.delete(k):os.put(v,k)}catch(e){}}
  window.KV={get:function(k){return MEM.has(k)?MEM.get(k):null},set:function(k,v){v=String(v);MEM.set(k,v);put(k,v)},del:function(k){MEM.delete(k);put(k,null)}};
  function start(){
    if(started)return;started=true;
    try{for(var i=0;i<localStorage.length;i++){var k=localStorage.key(i);if(!MEM.has(k)){MEM.set(k,localStorage.getItem(k));put(k,MEM.get(k))}}}catch(e){}
    var s=document.createElement("script");s.textContent=document.getElementById("app").textContent;document.body.appendChild(s);
  }
  try{
    var rq=indexedDB.open("hangul-drills",1);
    rq.onupgradeneeded=function(){rq.result.createObjectStore("kv")};
    rq.onsuccess=function(){db=rq.result;try{var cur=db.transaction("kv").objectStore("kv").openCursor();cur.onsuccess=function(){var c=cur.result;if(c){MEM.set(c.key,c.value);c.continue()}else start()};cur.onerror=start}catch(e){start()}};
    rq.onerror=rq.onblocked=start;
  }catch(e){start()}
  setTimeout(start,3000);
  try{navigator.storage&&navigator.storage.persist&&navigator.storage.persist()}catch(e){}
  if("serviceWorker" in navigator&&/^https?:$/.test(location.protocol))addEventListener("load",function(){navigator.serviceWorker.register("sw.js").catch(function(){})});
})();
</script>
'''
src = src.replace("</body>", LOADER + "</body>", 1)
open(os.path.join(HERE, "index.html"), "w", encoding="utf8", newline="\n").write(src)

# ---- manifest ----
open(os.path.join(HERE, "manifest.webmanifest"), "w", encoding="utf8").write(f'''{{
  "name": "Matt's Hangul Drills",
  "short_name": "Hangul",
  "start_url": "./",
  "scope": "./",
  "display": "standalone",
  "orientation": "any",
  "background_color": "{GROUND}",
  "theme_color": "{GROUND}",
  "icons": [
    {{"src": "icons/icon-192.png", "sizes": "192x192", "type": "image/png"}},
    {{"src": "icons/icon-512.png", "sizes": "512x512", "type": "image/png"}},
    {{"src": "icons/maskable-512.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable"}}
  ]
}}
''')

# ---- service worker: precache everything, serve cache-first, refresh in the background ----
assets = ["./", "index.html", "manifest.webmanifest"] + sorted(
    "icons/" + f for f in os.listdir(os.path.join(HERE, "icons")) if f.endswith(".png")) + sorted(
    "fonts/" + f for f in os.listdir(os.path.join(HERE, "fonts")) if f.endswith(".woff2"))
h = hashlib.sha1()
for a in assets[1:]:
    h.update(open(os.path.join(HERE, a), "rb").read())
version = h.hexdigest()[:10]
open(os.path.join(HERE, "sw.js"), "w", encoding="utf8").write(f'''const CACHE="hangul-drills-{version}";
const ASSETS={assets!r};
self.addEventListener("install",e=>{{e.waitUntil(caches.open(CACHE).then(c=>c.addAll(ASSETS)).then(()=>self.skipWaiting()))}});
self.addEventListener("activate",e=>{{e.waitUntil(caches.keys().then(ks=>Promise.all(ks.filter(k=>k.startsWith("hangul-drills-")&&k!==CACHE).map(k=>caches.delete(k)))).then(()=>self.clients.claim()))}});
self.addEventListener("fetch",e=>{{
  const r=e.request;if(r.method!=="GET"||new URL(r.url).origin!==location.origin)return;
  e.respondWith(caches.open(CACHE).then(async c=>{{
    const hit=await c.match(r,{{ignoreSearch:true}})||(r.mode==="navigate"?await c.match("index.html"):null);
    const net=fetch(r).then(res=>{{if(res.ok)c.put(r,res.clone());return res}}).catch(()=>hit);
    return hit||net;
  }}));
}});
''')

# ---- zip for Netlify Drop (files at the zip root) ----
zpath = os.path.join(os.path.dirname(HERE), "Hangul-Drills-PWA.zip")
with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
    for a in ["index.html", "manifest.webmanifest", "sw.js"] + assets[3:]:
        z.write(os.path.join(HERE, a), a)
print("built", version, "->", zpath)
