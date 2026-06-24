# 健康檢查端點應回傳 200 與服務資訊
GET {{host}}/
HTTP 200
[Asserts]
jsonpath "$.status" == "ok"
jsonpath "$.service" == "webhook-translate"
