# StockEcho systemd 작업 설치

저장소에 unit 파일을 추가하는 것만으로 운영 서버의 timer가 활성화되지는
않는다. 배포 후 운영 서버에서 다음 명령으로 unit을 설치하고 갱신한다.

```bash
sudo install -m 0644 deploy/systemd/stockecho-*.service /etc/systemd/system/
sudo install -m 0644 deploy/systemd/stockecho-*.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now \
  stockecho-collector.timer \
  stockecho-worker.timer \
  stockecho-risk-materializer.timer
```

과거 유사 사례 선계산 작업의 실행 여부는 다음 명령으로 확인한다.

```bash
systemctl list-timers stockecho-risk-materializer.timer
systemctl status stockecho-risk-materializer.service
journalctl -u stockecho-risk-materializer.service --since today
```

`stockecho-risk-materializer.service`는 현재 이슈 분석이 하나라도 실패하면
실패 상태를 반환한다. 실패를 해결한 뒤 아래 명령으로 즉시 다시 실행할 수
있다.

```bash
sudo systemctl start stockecho-risk-materializer.service
```
