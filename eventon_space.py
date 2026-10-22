"""Event ON: one geometry for plan, 3D, routes and PDF. Units are metres."""
import io, json, math, random
from pathlib import Path
import streamlit.components.v1 as components

COLORS={"공연장":"#8b5cf6","푸드존":"#f59e0b","체험 부스":"#3b82f6","휴게 공간":"#10b981","응급의료센터":"#ef4444","안내센터":"#06b6d4","화장실":"#64748b","굿즈 판매":"#ec4899"}
SIZES={"공연장":(12,7),"푸드존":(10,6),"체험 부스":(9,6),"휴게 공간":(10,7),"응급의료센터":(7,5),"안내센터":(6,4),"화장실":(6,4),"굿즈 판매":(7,5)}

def geometry(data):
    w=max(40.,float(data.get('site_width',90)));h=max(35.,float(data.get('site_depth',60)))
    shape=data.get('venue_shape','직사각형 (기본)')
    if shape=='정사각형': w=h=min(w,h)
    if shape in ('원형 광장','돔형 (지붕 있음)'): w=h=min(w,h)
    if shape in ('원형 광장','돔형 (지붕 있음)','타원형 경기장'):
        points=[(w/2+w/2*math.cos(i*math.tau/128),h/2+h/2*math.sin(i*math.tau/128)) for i in range(128)]
    elif shape=='L자형': points=[(0,0),(.58*w,0),(.58*w,.42*h),(w,.42*h),(w,h),(0,h)]
    else: points=[(0,0),(w,0),(w,h),(0,h)]
    # Gates are exactly on the lower boundary, including circular venues.
    def bottom(x):
        if shape in ('원형 광장','돔형 (지붕 있음)','타원형 경기장'):
            return h/2-h/2*math.sqrt(max(0,1-((x-w/2)/(w/2))**2))
        return 0
    gates=[{'name':'입구','x':.38*w,'y':bottom(.38*w),'color':'#10b981'}, {'name':'출구','x':.53*w,'y':bottom(.53*w),'color':'#f97316'}]
    return w,h,points,gates

def inside(x,y,poly):
    c=False;j=len(poly)-1
    for i,(xi,yi) in enumerate(poly):
        xj,yj=poly[j]
        if (yi>y)!=(yj>y) and x<(xj-xi)*(y-yi)/(yj-yi)+xi: c=not c
        j=i
    return c

def fits(x,y,bw,bh,poly,placed=(),clearance=1.5):
    # Perimeter sampling also catches the concave corner of an L-shaped venue.
    a,b=bw/2+clearance,bh/2+clearance
    for i in range(9):
        t=i/8
        for px,py in ((x-a+2*a*t,y-b),(x-a+2*a*t,y+b),(x-a,y-b+2*b*t),(x+a,y-b+2*b*t)):
            if not inside(px,py,poly): return False
    return all(abs(x-z['x'])>a+z['w']/2 or abs(y-z['y'])>b+z['h']/2 for z in placed)

def plan(data):
    w,h,poly,gates=geometry(data);placed=[];warnings=[]
    anchors={'공연장':(.5,.8),'푸드존':(.8,.65),'체험 부스':(.23,.55),'휴게 공간':(.75,.3),'응급의료센터':(.2,.25),'안내센터':(.35,.15),'화장실':(.15,.72),'굿즈 판매':(.72,.8)}
    saved=data.get('layout_positions',{}) or {}
    for name in dict.fromkeys(data.get('facilities',list(COLORS)[:6])):
        bw,bh=SIZES.get(name,(7,5));ax,ay=anchors.get(name,(.5,.5))
        requested=saved.get(name)
        if requested: ax,ay=map(float,requested)
        x,y=ax*w,ay*h
        if not fits(x,y,bw,bh,poly,placed):
            candidates=[(ix,iy) for ix in range(2,int(w),2) for iy in range(2,int(h),2) if fits(ix,iy,bw,bh,poly,placed)]
            if not candidates:
                warnings.append(name+'을 배치할 공간이 부족합니다. 행사장 크기를 늘리세요.');continue
            # Preserve a central north-south corridor whenever feasible.
            x,y=min(candidates,key=lambda p:(p[0]-ax*w)**2+(p[1]-ay*h)**2+max(0,3+bw/2-abs(p[0]-w/2))**2*4)
            if requested: warnings.append(name+'의 요청 좌표는 경계·시설 간격 조건에 맞게 보정됐습니다.')
        placed.append(dict(name=name,x=x,y=y,w=bw,h=bh,color=COLORS.get(name,'#64748b')))
    return dict(width=w,depth=h,polygon=poly,gates=gates,zones=placed,warnings=warnings,shape=data.get('venue_shape','직사각형 (기본)'),name=data.get('name','새 행사'),visitors=max(1,int(data.get('visitors',1000))))

def optimize_layout_candidates(data):
    result=[]
    for label,seed in [('균형 배치',7),('분산 배치',23),('접근 중심 배치',51)]:
        rng=random.Random(seed);candidate=dict(data)
        candidate['layout_positions']={n:(rng.uniform(.15,.85),rng.uniform(.2,.85)) for n in data.get('facilities',[])}
        p=plan(candidate)
        result.append({'name':label,'positions':{z['name']:(z['x']/p['width'],z['y']/p['depth']) for z in p['zones']},'warnings':p['warnings']})
    return result

def crowd_widget(data):
    p=plan(data)
    template=Path(__file__).with_name('space_viewer.html').read_text(encoding='utf-8')
    components.html(template.replace('__PAYLOAD__',json.dumps(p,ensure_ascii=False).replace('</','<\\/')),height=790,scrolling=True)
    return p

def make_layout_image(data,selected=None,path=None):
    import matplotlib.pyplot as plt
    from matplotlib.patches import Polygon,Rectangle
    from matplotlib import font_manager
    names={f.name for f in font_manager.fontManager.ttflist}
    for font in ('NanumGothic','Noto Sans CJK KR','Malgun Gothic','AppleGothic'):
        if font in names: plt.rcParams['font.family']=font;break
    plt.rcParams['axes.unicode_minus']=False
    p=plan(data);fig,ax=plt.subplots(figsize=(12,8),dpi=160);fig.patch.set_facecolor('#f8fafc');ax.set_facecolor('#f8fafc')
    floor=Polygon(p['polygon'],facecolor='#eef2f6',edgecolor='#475569',linewidth=1.6);ax.add_patch(floor)
    for x in range(0,int(p['width'])+1,5):
        line=ax.plot([x,x],[0,p['depth']],color='#d9e1eb',lw=.5)[0];line.set_clip_path(floor)
    for y in range(0,int(p['depth'])+1,5):
        line=ax.plot([0,p['width']],[y,y],color='#d9e1eb',lw=.5)[0];line.set_clip_path(floor)
    for z in p['zones']:
        ax.add_patch(Rectangle((z['x']-z['w']/2,z['y']-z['h']/2),z['w'],z['h'],facecolor=z['color'],alpha=.75,edgecolor='#0f172a' if selected==z['name'] else 'white',lw=2))
        ax.text(z['x'],z['y'],z['name'],ha='center',va='center',fontsize=8,color='#0f172a',weight='bold')
        ax.text(z['x'],z['y']-z['h']/2-1.1,f"{z['w']:g} × {z['h']:g} m",ha='center',va='top',fontsize=6,color='#475569')
    for g in p['gates']:
        ax.scatter([g['x']],[g['y']],c=g['color'],s=70,zorder=9);ax.text(g['x'],g['y']-2.4,g['name'],ha='center',fontsize=8)
    ax.plot([2,12],[-6,-6],color='#334155',lw=3);ax.text(7,-5.3,'10 m',ha='center',fontsize=8)
    ax.set_title(p['name']+' | '+p['shape'],loc='left',fontsize=15,pad=15)
    ax.set_xlim(-4,p['width']+4);ax.set_ylim(-9,p['depth']+5);ax.set_aspect('equal');ax.axis('off')
    fig.text(.12,.02,'기획용 개념 배치도 · 입력 치수 기준 · 현장 실측 및 안전 검토 필요',fontsize=8,color='#64748b')
    out=path or io.BytesIO();fig.savefig(out,format='png',bbox_inches='tight');plt.close(fig)
    if path:return path
    out.seek(0);return out
