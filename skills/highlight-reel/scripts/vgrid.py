"""Usage: vgrid.py SRC.MP4|CLIP_NAME START END OUT.jpg [fps=5]   (OUT relative → workspace grids/)
5 fps review grid with an x-position ruler (0-100) and team-colour player boxes, for writing the shot list."""
import sys,os,subprocess,glob,cv2,tempfile
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__))); from detect import team_blobs
import hrstate
src,a,b,out=sys.argv[1],float(sys.argv[2]),float(sys.argv[3]),sys.argv[4]; out=out if os.path.isabs(out) else os.path.join(hrstate.sub('grids'),out); fps=float(sys.argv[5]) if len(sys.argv)>5 else 5
if not os.path.exists(src): src=hrstate.get(f'media.clips.{src}.path') or sys.exit(f'unknown clip {sys.argv[1]}')
d=tempfile.mkdtemp()
subprocess.run(['/opt/homebrew/bin/ffmpeg','-nostdin','-v','error','-ss',str(a),'-i',src,'-t',str(b-a),'-vf',f'fps={fps},scale=960:540','-q:v','3',f'{d}/g_%04d.jpg'],check=True)
tiles=[]
for i,f in enumerate(sorted(glob.glob(d+'/g_*.jpg'))):
    im=cv2.imread(f); vis=cv2.convertScaleAbs(im,alpha=1.5,beta=-40)
    for p in team_blobs(im): cv2.rectangle(vis,(p['x0'],p['y0']),(p['x1'],p['y1']),(255,200,0),1)
    for x in range(0,101,10):
        X=int(x*9.59); cv2.line(vis,(X,0),(X,14),(0,255,255),2); cv2.putText(vis,str(x),(X+2,30),0,0.55,(0,255,255),2)
    cv2.putText(vis,f'{a+i/fps:.1f}s',(820,525),0,0.9,(0,255,0),2); tiles.append(cv2.resize(vis,(480,270)))
while len(tiles)%4: tiles.append(tiles[0]*0)
cv2.imwrite(out,cv2.vconcat([cv2.hconcat(tiles[i:i+4]) for i in range(0,len(tiles),4)]),[cv2.IMWRITE_JPEG_QUALITY,85])
print(out,len(tiles))
