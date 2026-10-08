"""4K torso-crop ID sheets: top 3 team-colour players per survey frame, 10 clips per sheet → sheets/crops_NN.jpg.
Usage: crops.py [CLIP...]  (default: all clips in sheets/blobs.json)"""
import os,json,sys
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import hrstate
F4=hrstate.sub('frames_4k'); SH=hrstate.sub('sheets')
from PIL import Image,ImageDraw,ImageFont
res=json.load(open(f'{SH}/blobs.json'))
font=ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc',18)
TW,TH=120,150; PER=3; ROWS=10; LW=110
def players(bl):
    bl=[b for b in bl if b['area']>=60]; groups=[]
    for b in sorted(bl,key=lambda b:-b['area']):
        for g in groups:
            if b['x1']>g['x0']-4 and b['x0']<g['x1']+4 and abs(b['cy']-g['cy'])<(g['y1']-g['y0'])*2.5:
                g['x0']=min(g['x0'],b['x0']);g['x1']=max(g['x1'],b['x1']);g['y0']=min(g['y0'],b['y0']);g['y1']=max(g['y1'],b['y1']);g['area']+=b['area'];break
        else: groups.append(dict(b))
    return sorted([g for g in groups if g['area']>=250],key=lambda g:-g['area'])
def crop(c,k,g):
    im=Image.open(f'{F4}/{c}/frame_{k}.jpg'); S=im.width/1280
    w=g['x1']-g['x0']; h=g['y1']-g['y0']; cx=(g['x0']+g['x1'])/2
    side=max(w,h*0.8)*1.3; top=g['y0']-h*0.35
    box=[int((cx-side/2)*S),int(top*S),int((cx+side/2)*S),int((top+side*1.25)*S)]
    t=im.crop(box).resize((TW,TH))
    # brighten log footage for readability
    from PIL import ImageOps; return ImageOps.autocontrast(t,cutoff=1)
if __name__=='__main__':
    clips=sys.argv[1:] or sorted(res)
    out=[]; 
    for c in clips:
        tiles=[]
        for k in range(5):
            for g in players(res[c][k])[:PER]: tiles.append((k,g))
        out.append((c,tiles))
    meta={}
    for s in range(0,len(out),ROWS):
        chunk=out[s:s+ROWS]; sheet=Image.new('RGB',(LW+15*TW,ROWS*(TH+20)),(15,15,15)); d=ImageDraw.Draw(sheet)
        for r,(c,tiles) in enumerate(chunk):
            y=r*(TH+20); d.text((4,y+60),c[-10:],fill=(255,255,0),font=font)
            for i,(k,g) in enumerate(tiles):
                sheet.paste(crop(c,k,g),(LW+i*TW,y+18)); d.text((LW+i*TW+3,y),f'f{k}',fill=(0,255,255),font=font)
                meta[f'{c}:{i}']=dict(frame=k,**g)
        n=s//ROWS+1; sheet.save(f'{SH}/crops_{n:02d}.jpg',quality=88)
    json.dump(meta,open(f'{SH}/crops_meta.json','w')); print('sheets',(len(out)+ROWS-1)//ROWS)
