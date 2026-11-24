const offline = location.protocol === 'file:';
let activeSocket;
let replayTimer;
let previousLeader;
let nextMilestone;

function showDrafts(notice = '') {
  const entries = VoteDrafts.list();
  const pending = entries.filter(entry => entry.status === 'pending').length;
  const unread = VoteDrafts.unread();
  const [latest] = VoteDrafts.approved(entries);
  set('arrival-count', unread ? '새 초안 도착 ' + unread + '건' : '검토 대기 ' + pending + '건');
  set('arrival-description', notice || (entries.length
    ? '검토 대기 ' + pending + '건 · 생성된 기사와 검토 결과를 확인할 수 있습니다.'
    : '집계가 진행되면 개표 기사 초안이 자동으로 생성됩니다.'));
  if (!latest) {
    set('draft-title', '서울시장 모의 개표');
    set('draft-body', '초안 검토에서 기사를 승인하면 여기에 표시됩니다.');
    set('draft-source', '승인된 기사 대기');
    set('paper-time', '—');
    return;
  }
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
  const changedLeader = leader && previousLeader && leader !== previousLeader;
  while (nextMilestone < 100 && frame.count_progress_pct >= nextMilestone) {
    generateDraft(nextMilestone + '% 도달');
    nextMilestone += 10;
  }
  if (changedLeader) generateDraft('선두 변경');
  if (frame.complete) generateDraft('최종 집계');
  if (leader) previousLeader = leader;
}

function startReplay() {
  previousLeader = null;
  nextMilestone = 10;
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
window.addEventListener('storage', () => showDrafts());
showDrafts();
if (offline) {
  const index = offlineFrames.findIndex(frame => frame.count_progress_pct >= 68.4);
  for (const frame of offlineFrames.slice(0, index + 1)) render(frame);
  set('feed-status', '내장 예시 집계');
} else {
  startReplay();
}
