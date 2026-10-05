import json,urllib.request,urllib.parse,collections,sys
def search(q):
    u="https://api.turath.io/search?"+urllib.parse.urlencode({"q":q,"ver":3})
    import subprocess; d=json.loads(subprocess.run(["curl","-s","-m","30",u],capture_output=True).stdout.decode(),strict=False)
    c=collections.Counter()
    for h in d["data"]:
        m=json.loads(h["meta"],strict=False); c[(h["book_id"],m["book_name"],m["author_name"])]+=1
    return d["count"],c
# A phrase from the Zad matn opening of Kitab al-Tahara
for q in sys.argv[1:]:
    n,c=search(q); print("##",q,n)
    for k,v in c.most_common(25): print(" ",v,k)
