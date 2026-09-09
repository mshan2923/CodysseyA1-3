import json,os
from datetime import date
from http.server import BaseHTTPRequestHandler
import requests

AI_URL=os.getenv("AI_URL","https://copa.codyssey.kr/v1/chat/completions")
AI_MODEL=os.getenv("AI_MODEL","gpt-5-mini")
LOCAL_URL="https://dapi.kakao.com/v2/local/search/keyword.json"
ROUTE_URL="https://apis-navi.kakaomobility.com/v1/directions"

def reply(h,status,data):
    b=json.dumps(data,ensure_ascii=False).encode()
    h.send_response(status);h.send_header("Content-Type","application/json; charset=utf-8");h.end_headers();h.wfile.write(b)

def ai(messages):
    # 배포(Vercel) 기본값은 Codyssey 원격 API. 로컬에서 Ollama 등 키 없는 엔드포인트로 테스트하려면
    # .env에 AI_URL/AI_MODEL만 지정하면 되고, 그 경우 CODYSSEY_API_KEY가 없어도 헤더 없이 요청함.
    key=os.getenv("CODYSSEY_API_KEY")
    if not key and "codyssey" in AI_URL:
        raise RuntimeError("CODYSSEY_API_KEY 환경 변수가 없습니다.")
    headers={"Authorization":f"Bearer {key}"} if key else {}
    r=requests.post(AI_URL,headers=headers,json={"model":AI_MODEL,"messages":messages,"stream":False},timeout=90)
    r.raise_for_status();return r.json()["choices"][0]["message"]["content"]

def json_text(s):
    s=s.strip()
    if s.startswith("```"):s=s.split("\n",1)[1].rsplit("```",1)[0]
    a,b=s.find("{"),s.rfind("}")
    if a<0 or b<0:raise ValueError("AI JSON 응답을 찾지 못했습니다.")
    return json.loads(s[a:b+1])

def make_prompt(p):
    styles = ", ".join(p["styles"]) if p["styles"] else "특별한 스타일 없음"
    custom = p["custom_style"] or "없음"

    return f"""
한국 국내여행 전문 플래너다.

사용자가 입력한 날짜와 여행 스타일을 바탕으로 국내 여행지 1곳을 추천하고,
해당 여행지에서 날짜별 여행 일정을 만들어라.

사용자 입력:
- 시작일: {p["start_date"]}
- 종료일: {p["end_date"]}
- 여행 스타일: {styles}
- 추가 요청: {custom}

반드시 아래 JSON 구조로만 응답하라.
Markdown 코드 블록을 사용하지 마라.

{{
  "destination": {{
    "name": "지역명",
    "reason": "이 여행지를 추천하는 이유를 2~3문장으로 작성"
  }},
  "days": [
    {{
      "day": 1,
      "date": "YYYY-MM-DD",
      "places": [
        {{
          "name": "실제로 존재하는 장소명",
          "category": "관광",
          "start_time": "09:30",
          "end_time": "11:00",
          "reason": "이 장소를 추천하는 이유"
        }}
      ]
    }}
  ]
}}

규칙:
1. days의 개수는 여행 기간과 정확히 일치해야 한다.
2. 각 날짜는 사용자가 입력한 날짜를 그대로 사용한다.
3. 하루에 3~5개의 장소를 추천한다.
4. 실제로 존재하는 장소를 우선한다.
5. 존재하지 않는 장소를 만들지 않는다.
6. 같은 장소를 반복해서 추천하지 않는다.
7. 이동 동선이 자연스럽도록 일정을 구성한다.
8. 여행 스타일을 일정에 적극적으로 반영한다.
9. 장소명은 Kakao Local API에서 검색할 수 있을 정도로 구체적으로 작성한다.
10. 날짜에 실제로 개최되는 행사라고 확신할 수 없는 경우 행사를 만들어내지 않는다.
11. JSON 이외의 설명은 절대 출력하지 않는다.
"""
def validate(x,p):
    if not x.get("destination",{}).get("name") or not isinstance(x.get("days"),list):raise ValueError("AI 응답 구조가 올바르지 않습니다.")
    a=date.fromisoformat(p["start_date"]);b=date.fromisoformat(p["end_date"])
    expected=[date.fromordinal(a.toordinal()+i).isoformat() for i in range((b-a).days+1)]
    if len(x["days"])!=len(expected):raise ValueError("AI가 생성한 여행 일수가 입력과 다릅니다.")
    for i,d in enumerate(x["days"]):
        if d.get("day")!=i+1 or d.get("date")!=expected[i] or not d.get("places"):raise ValueError("AI 일정의 날짜 정보가 올바르지 않습니다.")

def place(name,region):
    key=os.getenv("KAKAO_REST_API_KEY")
    if not key:raise RuntimeError("KAKAO_REST_API_KEY 환경 변수가 없습니다.")
    r=requests.get(LOCAL_URL,headers={"Authorization":f"KakaoAK {key}"},params={"query":f"{region} {name}","size":5},timeout=10)
    r.raise_for_status();docs=r.json().get("documents",[])
    if not docs:return None
    x=docs[0];return {"name":x.get("place_name",name),"address":x.get("road_address_name") or x.get("address_name",""),"lat":float(x["y"]),"lng":float(x["x"]),"place_url":x.get("place_url","")}

def resolve(x):
    region=x["destination"]["name"]
    for d in x["days"]:
        for p in d["places"]:
            try:
                q=place(p["name"],region)
                p.update(q or {"address":"","lat":None,"lng":None,"place_url":""})
            except Exception:
                p.update({"address":"","lat":None,"lng":None,"place_url":""})
    return x

def route(places):
    pts=[p for p in places if p.get("lat") is not None and p.get("lng") is not None]
    if len(pts)<2 or not os.getenv("KAKAO_REST_API_KEY"):return None
    params={"origin":f'{pts[0]["lng"]},{pts[0]["lat"]}',"destination":f'{pts[-1]["lng"]},{pts[-1]["lat"]}',"priority":"RECOMMEND","summary":"true"}
    if len(pts)>2:params["waypoints"]="|".join(f'{p["lng"]},{p["lat"]}' for p in pts[1:-1][:5])
    try:
        r=requests.get(ROUTE_URL,headers={"Authorization":f'KakaoAK {os.getenv("KAKAO_REST_API_KEY")}'},params=params,timeout=12);r.raise_for_status()
        s=(r.json().get("routes") or [{}])[0].get("summary",{})
        return {"distance_m":s.get("distance"),"duration_s":s.get("duration")}
    except requests.RequestException:return None

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            n=int(self.headers.get("Content-Length","0"));p=json.loads(self.rfile.read(n))
            if not p.get("start_date") or not p.get("end_date"):return reply(self,400,{"error":"여행 날짜를 입력해주세요."})
            a=date.fromisoformat(p["start_date"]);b=date.fromisoformat(p["end_date"])
            if (b-a).days not in range(0,7):return reply(self,400,{"error":"여행 기간은 1~7일로 설정해주세요."})
            clean={"start_date":p["start_date"],"end_date":p["end_date"],"styles":p.get("styles",[])[:9],"custom_style":str(p.get("custom_style",""))[:300]}
            msg=[{"role":"system","content":"JSON으로만 답하는 국내 여행 플래너다."},{"role":"user","content":make_prompt(clean)}]
            err=None
            for _ in range(2):
                try:
                    x=json_text(ai(msg));validate(x,clean);break
                except Exception as e:
                    err=e;msg += [{"role":"user","content":"직전 응답을 수정하세요. 요구한 JSON만 반환하고 날짜 수를 정확히 맞추세요."}]
            else:raise ValueError(f"AI 일정 생성 실패: {err}")
            x=resolve(x)
            for d in x["days"]:d["route"]=route(d["places"])
            reply(self,200,x)
        except requests.Timeout:reply(self,504,{"error":"외부 API 응답이 늦습니다. 잠시 후 다시 시도해주세요."})
        except requests.RequestException:reply(self,502,{"error":"외부 API 요청에 실패했습니다. 잠시 후 다시 시도해주세요."})
        except ValueError as e:reply(self,400,{"error":str(e)})
        except Exception as e:
            print(e);reply(self,500,{"error":"여행 계획을 만드는 중 문제가 발생했습니다."})
