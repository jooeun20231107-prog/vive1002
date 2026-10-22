# Event ON — Space Studio

행사 공간 설계 부분을 교체하는 Streamlit 실행 예제입니다. 계정 시스템을 포함한 기존 앱 전체를 복원한 파일은 아닙니다.

## GitHub → Streamlit Community Cloud

아래 파일을 GitHub 저장소 루트에 올립니다.

- `app.py`: 실행 화면
- `eventon_space.py`: 공통 좌표·시설 배치·PNG 출력
- `space_viewer.html`: 2D/3D 및 이동 시뮬레이션
- `requirements.txt`: Python 의존성
- `packages.txt`: 한국어 폰트

Streamlit Community Cloud에서 저장소를 연결하고 Main file path를 `app.py`로 설정합니다. 로컬 실행은 `pip install -r requirements.txt` 다음 `streamlit run app.py`입니다. 별도 API 키는 필요 없습니다. 3D 라이브러리는 cdnjs에서 불러옵니다. CDN이 차단되면 2D는 동작하지만 3D는 사용할 수 없습니다.

## 바뀐 부분

1. 미터 단위 XY 좌표를 2D·3D·PNG·PDF가 공유합니다. 북쪽이 +Y이며 3D에서는 -Z입니다.
2. 시설 중심만이 아니라 시설 면적과 1.5 m 여유를 확인합니다. L자형의 오목한 모서리도 시설 둘레를 샘플링해 확인합니다.
3. 출입구는 원형에서도 실제 경계 위에 놓입니다. 사람은 각 게이트에서 가장 가까운 내부 이동 셀에서 시작/종료합니다. 표시된 게이트와 해당 셀 사이의 경계 구간은 실제 출입구 폭을 모델링한 것이 아닙니다.
4. 1 m 격자의 자유 공간에서 BFS 경로를 찾습니다. 벽·부스 안으로 직선 이동하거나 대각선 모서리를 가로지르지 않습니다. 이동 위치는 도착 후 잠시 머물렀다가 다음 목적지로 이어집니다.
5. 시설 클릭 시 입구에서 시설 접근점까지의 경로가 나타납니다. 접근점은 시설 앞의 가장 가까운 자유 셀로 단순화했습니다. 부스 실내 출입/문 위치는 별도 모델링하지 않습니다.
6. ‘체류 분포’는 시뮬레이션 에이전트의 누적 위치 빈도이며 실제 인구 밀도가 아닙니다.
7. 배치 후보에 임의의 100점 만점 안전 점수를 붙이지 않습니다. 세 후보는 시드가 고정된 초기 위치 + 기하 조건 검사로 생성하며 수학적 최적해 보장은 없습니다.
8. 적용된 좌표를 JSON으로 저장하고 동일한 설계도를 PNG/PDF로 내보냅니다.

## 기존 코드에 시각화만 연결하기

원래 Python 파일이 문법적으로 실행 가능한 상태여야 합니다. 대화창에 붙여넣은 코드에는 점(.)·소수점·들여쓰기 등이 손상된 부분이 많아, 그 텍스트에 아래 두 줄만 추가한다고 전체 앱이 복구되는 것은 아닙니다. 실제 원본 `.py` 파일을 기준으로 작업하세요.

1. `eventon_space.py`, `space_viewer.html`을 원래 앱 파일과 같은 폴더에 둡니다.
2. 원래 코드의 `make_layout_image`와 `crowd_widget` 함수 정의를 제거하고 아래 import로 대체합니다. 또는 **두 함수의 기존 정의 이후, Auth/화면 실행 이전**에 아래 import를 넣어 재정의합니다.

```python
from eventon_space import crowd_widget, make_layout_image
```

3. 기존 `crowd_widget(data)` / `make_layout_image(data)` / `make_layout_image(data, path=img_path)` 호출은 그대로 사용할 수 있습니다. 기존 PDF는 PNG 결과를 그대로 사용합니다.
4. 기존 `event_data`에 선택적으로 `site_width`, `site_depth`를 추가합니다. 생략하면 90 × 60 m 예시 크기입니다. `layout_positions`는 기존처럼 0~1 상대 좌표입니다.
5. 새 `plan(data)`는 경계를 벗어나거나 겹치는 좌표를 자동 보정합니다. 기존 SQLite에 **보정 후 좌표**를 기록하려면 기존 저장 처리 직전에 다음처럼 반영하세요.

```python
from eventon_space import plan
p = plan(data)
data['layout_positions'] = {
    z['name']: (z['x'] / p['width'], z['y'] / p['depth'])
    for z in p['zones']
}
save_project(username, data)
```

기존 `positions()`는 새 도면과 좌표 보정 방식이 다릅니다. 기존 슬라이더 초기값도 위 `plan(data)` 결과를 기준으로 바꿔야 화면과 일치합니다. 새 app.py는 이미 이 방식입니다.

**주의:** 새 모듈의 `optimize_layout_candidates`는 기존 함수와 결과 형식이 다릅니다. 기존 앱의 후보 카드에 필요한 `score`와 `metrics`를 의도적으로 반환하지 않으므로 그대로 바꿔 끼우지 마세요. 위 두 시각화 함수만 연결하면 원래 최적화 함수는 유지됩니다. 기존 점수는 새 엔진에서 검증된 값이 아닙니다. 후보 UI까지 바꿀 때는 새 app.py의 ‘다른 배치 탐색’을 참고하세요.

## 한계와 운영 전 확인

- 실제 디지털 트윈에는 실측 도면, 정확한 시설 치수, 출입구 폭·문 위치, 고정 장애물, 관측 인원 및 실제 이동 기록 연결이 추가로 필요합니다.
- 시설 크기·1.5 m 여유·표시 인원·속도·체류시간은 데모 가정입니다. 법정 기준이나 안전성 검증 결과가 아닙니다.
- 이동 에이전트끼리의 충돌 회피, 줄서기, 압력, 대피, 장애인 접근성, 휠체어 회전 폭, 병목 처리 용량은 계산하지 않습니다.
- 원래 코드의 비밀번호 단순 SHA-256 저장은 서비스 운영 전에 솔트가 있는 적응형 비밀번호 해시 등으로 교체하고, 인증·DB 영속성도 별도로 보강해야 합니다.
- 한국어 PNG 글꼴은 Cloud 빌드 시 packages.txt의 fonts-nanum 설치를 사용합니다.
- 이 배포물은 Python 문법·공통 배치 기하·PNG 출력·JavaScript 문법을 검사했습니다. 여기서 Streamlit 실제 웹 세션이나 브라우저 WebGL을 실행해 시각 확인한 것은 아닙니다. 첫 배포 시 2D/3D 전환, L자형, 시설 좌표 적용, JSON 복원, PNG/PDF 다운로드를 확인하세요.
