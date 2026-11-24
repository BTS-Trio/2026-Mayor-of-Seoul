const offline = location.protocol === 'file:';
let activeSocket;
let replayTimer;
let previousLeader;
let halfway;

function showDrafts(notice = '') {
  const entries = VoteDrafts.list();
  const pending = entries.filter(entry => entry.status === 'pending').length;
  const latest = entries.at(-1);
  set('arrival-count', '검토 대기 ' + pending + '건');
  set('arrival-description', notice || (latest
    ? '생성된 개표 기사와 검토 결과를 확인할 수 있습니다.'
    : '집계가 진행되면 개표 기사 초안이 자동으로 생성됩니다.'));
  get('review-link').setAttribute('aria-disabled', String(!latest));
  if (!latest) return;
  set('draft-title', latest.title);
  set('draft-body', latest.body);
  set('draft-source', latest.source);
  set('paper-time', latest.time);
}

function generateDraft(reason) {
  if (lastFrame?.counted_ballots && VoteDrafts.create(lastFrame, reason, offline ? 'sample' : 'feed')) {
    showDrafts('새 개표 기사 초안이 도착했습니다.');
  }
}

function receiveFrame(frame) {
  render(frame);
  set('feed-status', frame.complete ? '모의 개표 완료' : '모의 개표 재생 중 · ' + frame.count_progress_pct.toFixed(1) + '%');
  if (!frame.counted_ballots) return;
  const [first, second] = [...frame.candidates].sort((a, b) => b.votes - a.votes);
  const leader = first.votes > second.votes ? first.candidate_id : null;
  const crossedHalfway = !halfway && frame.count_progress_pct >= 50;
  const changedLeader = leader && previousLeader && leader !== previousLeader;
  if (frame.complete) generateDraft('최종 집계');
  else if (crossedHalfway) generateDraft('중간 집계');
  else if (changedLeader) generateDraft('선두 변경');
  if (crossedHalfway) halfway = true;
  if (leader) previousLeader = leader;
}

function startReplay() {
  designFrames.length = 0;
  previousLeader = null;
  halfway = false;
  if (offline) {
    clearInterval(replayTimer);
    let position = 0;
    receiveFrame(offlineFrames[position]);
    replayTimer = setInterval(() => {
      const frame = offlineFrames[++position];
      receiveFrame(frame);
      if (frame.complete) clearInterval(replayTimer);
    }, 2000);
    return;
  }
  activeSocket?.close();
  const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
  const connection = new WebSocket(protocol + '//' + location.host + '/ws/replay');
  activeSocket = connection;
  set('feed-status', '개표 피드 연결 중');
  let finished = false;
  connection.addEventListener('message', event => {
    if (activeSocket !== connection) return;
    const frame = JSON.parse(event.data);
    if (frame.event === 'error') {
      finished = true;
      set('feed-status', frame.message);
      return;
    }
    receiveFrame(frame);
    finished = frame.complete;
  });
  connection.addEventListener('close', () => {
    if (activeSocket === connection && !finished) {
      set('feed-status', '개표 피드 연결이 끊겼습니다. 다시 재생해 주세요.');
    }
  });
}

get('replay-feed').addEventListener('click', startReplay);
get('build-draft').addEventListener('click', () => generateDraft('수동 생성'));
window.addEventListener('pageshow', () => showDrafts());
drawTrend();
showDrafts();
if (offline) {
  const index = offlineFrames.findIndex(frame => frame.count_progress_pct >= 68.4);
  for (const frame of offlineFrames.slice(0, index + 1)) render(frame);
  set('feed-status', '내장 예시 집계');
} else {
  startReplay();
}
