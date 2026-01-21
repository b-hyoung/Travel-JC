# 네이버 지도 API 연동 가이드 (버스 길찾기)

이 문서는 Django 웹 애플리케이션에 네이버 지도 API를 연동하여 현재 위치를 기반으로 버스 길찾기 기능을 구현하는 방법을 안내합니다.

## 개요

사용자의 현재 위치를 가져와 지도에 표시하고, 목적지까지의 버스 경로와 하차 지점 정보를 안내하는 기능을 구현합니다.

## 사전 준비

- **네이버 클라우드 플랫폼 API 키 발급**
  - 길찾기 기능을 사용하려면 네이버 클라우드 플랫폼에서 **Application을 등록**하고 **Client ID**와 **Client Secret**을 발급받아야 합니다.
  - 아래 가이드를 참고하여 키를 발급받으세요.
  - [Maps API 시작하기](https://ncloud-docs.com/ko/map-geolocation/maps/start/)
  - [Application 등록 가이드](https://ncloud-docs.com/ko/map-geolocation/maps/application/)

## 구현 단계

### 1. 백엔드 설정 (Django)

#### 1.1. API 키 설정

- 발급받은 **Client ID**와 **Client Secret**을 `django_web/config/settings.py` 또는 별도의 설정 파일에 추가합니다. 외부에 노출되지 않도록 환경 변수로 관리하는 것을 권장합니다.

```python
# config/settings.py

# ...
NAVER_MAP_CLIENT_ID = 'YOUR_CLIENT_ID'
NAVER_MAP_CLIENT_SECRET = 'YOUR_CLIENT_SECRET'
```

#### 1.2. URL 경로 추가

- 길찾기 페이지를 보여줄 URL과 길찾기 API를 호출할 URL을 `django_web/config/urls.py` 에 추가합니다.

```python
# config/urls.py

from django.urls import path
from . import views # 가정: views.py를 같은 디렉토리에 생성

urlpatterns = [
    # ... 기존 URL ...
    path('directions/', views.directions_page, name='directions_page'),
    path('api/directions/', views.get_directions, name='get_directions_api'),
]
```

#### 1.3. 뷰(View) 생성

- `django_web/config/views.py` 파일을 생성하거나 기존 파일에 다음 두 개의 뷰 함수를 추가합니다.

- **`directions_page`**: 지도를 표시할 HTML 페이지를 렌더링합니다.
- **`get_directions`**: 클라이언트의 요청을 받아 네이버 길찾기 API를 호출하고 결과를 반환합니다.

```python
# config/views.py

from django.shortcuts import render
from django.http import JsonResponse
from django.conf import settings
import requests

def directions_page(request):
    """지도를 보여줄 페이지를 렌더링합니다."""
    context = {
        'naver_map_client_id': settings.NAVER_MAP_CLIENT_ID
    }
    return render(request, 'directions.html', context)

def get_directions(request):
    """네이버 길찾기 API를 호출하고 결과를 JSON으로 반환합니다."""
    start = request.GET.get('start') # "lng,lat"
    goal = request.GET.get('goal')   # "lng,lat"

    if not start or not goal:
        return JsonResponse({'error': 'start와 goal 파라미터가 필요합니다.'}, status=400)

    headers = {
        "X-NCP-APIGW-API-KEY-ID": settings.NAVER_MAP_CLIENT_ID,
        "X-NCP-APIGW-API-KEY": settings.NAVER_MAP_CLIENT_SECRET,
    }
    
    url = f"https://naveropenapi.apigw.ntruss.com/map-direction/v1/driving?start={start}&goal={goal}&option=trafast" # 대중교통 옵션으로 변경 필요

    response = requests.get(url, headers=headers)
    
    return JsonResponse(response.json())
```
**참고:** 위 예제는 `driving`(자동차) 기준이며, 실제 구현 시에는 `trafast`(실시간 빠른길) 대신 `traoptimal`(대중교통 최적) 등 버스 길찾기에 맞는 옵션을 사용해야 합니다. [Directions API 가이드](https://ncloud-docs.com/ko/map-geolocation/directions-5/api-reference-guide/)를 참고하세요.

### 2. 프론트엔드 구현 (HTML/JavaScript)

#### 2.1. HTML 템플릿 생성

- `django_web/templates/directions.html` 파일을 생성합니다.

```html
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>네이버 지도를 이용한 길찾기</title>
    <script type="text/javascript" src="https://oapi.map.naver.com/openapi/v3/maps.js?ncpClientId={{ naver_map_client_id }}"></script>
    <style>
        #map {
            width: 100%;
            height: 600px;
        }
        #directions-info {
            margin-top: 10px;
            padding: 10px;
            border: 1px solid #ccc;
            height: 200px;
            overflow-y: auto;
        }
    </style>
</head>
<body>
    <h1>버스 길찾기</h1>
    <div id="map"></div>
    <div id="directions-info">
        <p>길찾기 안내가 여기에 표시됩니다.</p>
    </div>

    <script>
        // 3.2. JavaScript 코드 구현
    </script>
</body>
</html>
```

#### 2.2. JavaScript 코드 구현

- `directions.html` 파일 내의 `<script>` 태그 안에 다음 코드를 작성합니다.

```javascript
// 지도를 초기화하고 현재 위치를 가져옵니다.
var map = new naver.maps.Map('map', {
    center: new naver.maps.LatLng(37.3595704, 127.105399), // 기본 중심 위치
    zoom: 15
});

var currentPosition;

// 브라우저 Geolocation API로 현재 위치 가져오기
if (navigator.geolocation) {
    navigator.geolocation.getCurrentPosition(function(position) {
        var lat = position.coords.latitude;
        var lng = position.coords.longitude;
        currentPosition = new naver.maps.LatLng(lat, lng);
        
        // 지도의 중심을 현재 위치로 이동
        map.setCenter(currentPosition);

        // 현재 위치에 마커 표시
        new naver.maps.Marker({
            position: currentPosition,
            map: map,
            title: '현재 위치'
        });

        // 예시: 전주역을 목적지로 길찾기 요청
        var goalPosition = '127.14437,35.84834'; // 경도, 위도 순서
        getBusDirections(lng + ',' + lat, goalPosition);

    }, function() {
        alert('현재 위치를 가져오는 데 실패했습니다.');
    });
} else {
    alert('이 브라우저에서는 Geolocation을 지원하지 않습니다.');
}

// Django 백엔드를 통해 길찾기 API를 호출하는 함수
function getBusDirections(start, goal) {
    fetch(`/api/directions/?start=${start}&goal=${goal}`)
        .then(response => response.json())
        .then(data => {
            if (data.route && data.route.traoptimal) { // 대중교통 경로가 있는 경우
                const path = data.route.traoptimal[0].path;
                
                // 지도에 경로 그리기
                new naver.maps.Polyline({
                    path: path.map(p => new naver.maps.LatLng(p[1], p[0])),
                    strokeColor: '#5347AA',
                    strokeWeight: 3,
                    map: map
                });

                // 경로 안내 정보 표시
                displayDirections(data.route.traoptimal[0].summary);
            } else {
                document.getElementById('directions-info').innerText = '경로를 찾을 수 없습니다.';
                console.error(' 길찾기 오류:', data.message);
            }
        })
        .catch(error => {
            console.error('API 호출 중 오류 발생:', error);
            document.getElementById('directions-info').innerText = '길찾기 중 오류가 발생했습니다.';
        });
}

// 길찾기 안내를 화면에 표시하는 함수
function displayDirections(summary) {
    const infoDiv = document.getElementById('directions-info');
    infoDiv.innerHTML = '<h3>길찾기 요약</h3>';
    
    // 네이버 Directions API 응답 구조에 따라 상세 안내를 파싱하여 표시해야 합니다.
    // 예를 들어, 버스 번호, 탑승 정류장, 하차 정류장 정보를 추출하여 보여줍니다.
    
    // 예시: 요약 정보 (실제로는 summary 객체를 파싱해야 함)
    let summaryText = `
        <p>총 이동 시간: ${Math.round(summary.duration / 60000)}분</p>
        <p>총 거리: ${summary.distance}m</p>
        <p>하차 지점: API 응답을 파싱하여 여기에 표시</p> 
    `;

    infoDiv.innerHTML += summaryText;
}
```

## 파일 구조

이 작업을 완료하면 다음과 같은 파일들이 생성/수정됩니다.

```
django_web/
├── config/
│   ├── settings.py  (수정됨)
│   ├── urls.py      (수정됨)
│   └── views.py       (수정 또는 생성됨)
├── templates/
│   └── directions.html (생성됨)
└── naver_map_integration.md (생성됨)
```

## 다음 단계

1.  `settings.py`에 발급받은 네이버 API 키를 입력합니다.
2.  `pip install requests` 명령어로 `requests` 라이브러리를 설치합니다.
3.  Django 개발 서버를 실행하고 `http://127.0.0.1:8000/directions/`로 접속하여 결과를 확인합니다.
4.  네이버 지도 **Directions API**의 응답 형식을 참고하여 `displayDirections` 함수를 목적에 맞게 상세히 구현합니다. (예: 버스 노선, 하차 정류장 이름 표시)
