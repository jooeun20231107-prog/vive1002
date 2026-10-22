import io
import json
import streamlit as st
from eventon_space import COLORS, plan, crowd_widget, make_layout_image, optimize_layout_candidates

st.set_page_config(page_title='Event ON · Space Studio',page_icon='🎪',layout='wide')
st.markdown('''<style>.block-container{max-width:1450px;padding-top:2rem}h1{letter-spacing:-.04em}[data-testid="stMetric"]{border:1px solid #e2e8f0;padding:16px;border-radius:12px}</style>''',unsafe_allow_html=True)
DEFAULT={'name':'봄맞이 문화축제','visitors':1200,'venue_shape':'직사각형 (기본)','site_width':90,'site_depth':60,'facilities':list(COLORS)[:6],'layout_positions':{}}
if 'design' not in st.session_state: st.session_state.design=dict(DEFAULT)
if 'revision' not in st.session_state: st.session_state.revision=0

def apply(data):
    st.session_state.design=data
    st.session_state.revision+=1
    st.session_state.pop('candidates',None)
    st.rerun()

with st.sidebar:
    st.title('🎪 Event ON')
    st.caption('SPACE DESIGN STUDIO')
    d=st.session_state.design
    with st.form('brief'):
        name=st.text_input('행사명',d['name'])
        shapes=['직사각형 (기본)','정사각형','원형 광장','돔형 (지붕 있음)','타원형 경기장','L자형']
        shape=st.selectbox('행사장 외곽',shapes,index=shapes.index(d['venue_shape']))
        w=st.number_input('가로 길이 (m)',40,200,int(d['site_width']),5)
        h=st.number_input('세로 길이 (m)',35,150,int(d['site_depth']),5)
        st.caption('정사각형·원형·돔형은 두 길이 중 작은 값을 한 변/지름으로 사용합니다. 초기 치수는 예시이며 현장 실측값으로 바꾸세요.')
        visitors=st.number_input('총 예상 방문객 (명)',1,100000,int(d['visitors']),100)
        facilities=st.multiselect('시설',list(COLORS),default=d['facilities'])
        if st.form_submit_button('배치 생성',type='primary',use_container_width=True):
            if not facilities: st.error('시설을 하나 이상 선택해 주세요.')
            else: apply(dict(name=name or '새 행사',visitors=visitors,venue_shape=shape,site_width=w,site_depth=h,facilities=facilities,layout_positions={}))
    st.divider()
    uploaded=st.file_uploader('저장한 설계 불러오기',type=['json'])
    if uploaded and st.button('불러오기 적용'):
        try:
            obj=json.load(uploaded)
            if not isinstance(obj,dict): raise ValueError('객체 형식이 아닙니다.')
            obj={**DEFAULT,**obj}
            if obj['venue_shape'] not in shapes: raise ValueError('지원하지 않는 행사장 형태')
            if not isinstance(obj['facilities'],list) or not obj['facilities'] or any(n not in COLORS for n in obj['facilities']): raise ValueError('시설 목록을 확인하세요.')
            if not 40<=float(obj['site_width'])<=200 or not 35<=float(obj['site_depth'])<=150: raise ValueError('행사장 치수 범위 오류')
            if not 1<=int(obj['visitors'])<=100000: raise ValueError('방문객 범위 오류')
            if not isinstance(obj['layout_positions'],dict):raise ValueError('좌표 형식 오류')
            for pos in obj['layout_positions'].values():
                if len(pos)!=2 or not all(0<=float(v)<=1 for v in pos):raise ValueError('좌표 범위 오류')
            apply(obj)
        except (ValueError,TypeError,KeyError) as e: st.error(f'파일을 읽을 수 없습니다: {e}')

st.caption('PLAN / SIMULATE / REFINE')
st.title('행사 공간을 설계하고, 이동을 확인하세요.')
st.caption('시설·외곽·출입구를 하나의 좌표계로 연결한 기획용 공간 시뮬레이터')
d=st.session_state.design
p=plan(d)
for warning in p['warnings']: st.warning(warning)
a,b,c=st.columns(3)
a.metric('행사장 크기',f"{p['width']:g} × {p['depth']:g} m")
b.metric('배치한 시설',f"{len(p['zones'])} / {len(d['facilities'])}")
c.metric('시설 사이 기본 여유', '1.5 m',help='배치용 가정값입니다. 법정 통로 폭이나 안전 인증을 의미하지 않습니다.')
main,editor=st.columns([3,1],gap='large')
with main:
    crowd_widget(d)
with editor:
    st.subheader('시설 위치 조정')
    st.caption('슬라이더는 시설 중심 위치입니다. 경계를 벗어나거나 겹치면 적용 시 보정됩니다.')
    if p['zones']:
        zone=st.selectbox('시설 선택',[z['name'] for z in p['zones']])
        z=next(z for z in p['zones'] if z['name']==zone)
        revision=st.session_state.revision
        with st.form(f'move_{zone}_{revision}'):
            x=st.slider('가로 위치 (%)',5,95,round(z['x']/p['width']*100),key=f'x_{zone}_{revision}')
            y=st.slider('세로 위치 (%)',5,95,round(z['y']/p['depth']*100),key=f'y_{zone}_{revision}')
            if st.form_submit_button('좌표 적용',use_container_width=True):
                new=dict(d);new['layout_positions']={v['name']:(v['x']/p['width'],v['y']/p['depth']) for v in p['zones']};new['layout_positions'][zone]=(x/100,y/100);apply(new)
        st.write(f"**시설 크기** · {z['w']:g} × {z['h']:g} m")
    st.divider()
    st.subheader('다른 배치 탐색')
    st.caption('경계와 시설 간격을 검사한 3개 후보입니다. 검증되지 않은 안전 점수는 표시하지 않습니다.')
    if st.button('배치 후보 만들기',use_container_width=True): st.session_state.candidates=optimize_layout_candidates(d)
    for i,candidate in enumerate(st.session_state.get('candidates',[])):
        if st.button(candidate['name']+' 적용',key=f'candidate_{i}',use_container_width=True):
            new=dict(d);new['layout_positions']=candidate['positions'];apply(new)
    st.divider()
    # Store the actual corrected layout, not the uncorrected slider request.
    actual=dict(d);actual['layout_positions']={z['name']:(z['x']/p['width'],z['y']/p['depth']) for z in p['zones']}
    st.download_button('설계 저장 · JSON',json.dumps(actual,ensure_ascii=False,indent=2),file_name='eventon_design.json',mime='application/json',use_container_width=True)
    image=make_layout_image(d).getvalue()
    st.download_button('평면 설계도 · PNG',image,file_name='eventon_plan.png',mime='image/png',use_container_width=True)
    if st.button('설계도 PDF 준비',use_container_width=True):
        from reportlab.pdfgen import canvas
        from reportlab.lib.utils import ImageReader
        from reportlab.lib.pagesizes import A4,landscape
        pdf=io.BytesIO();page=landscape(A4);out=canvas.Canvas(pdf,pagesize=page);out.drawImage(ImageReader(io.BytesIO(image)),20,20,width=page[0]-40,height=page[1]-40,preserveAspectRatio=True,anchor='c');out.showPage();out.save();st.download_button('PDF 다운로드',pdf.getvalue(),file_name='eventon_plan.pdf',mime='application/pdf',use_container_width=True)
st.info('현재 예제는 공간 설계 부분만 재구성했습니다. 회원가입·로그인·SQLite 저장·기존 전체 보고서는 포함하지 않습니다. JSON으로 저장하지 않은 작업은 세션 종료 시 사라질 수 있습니다. 3D는 인터넷 연결과 WebGL 지원이 필요합니다.')
