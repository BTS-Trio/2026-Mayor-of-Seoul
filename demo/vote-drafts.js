const VoteDrafts = (() => {
  const key = 'seoul-vote-drafts';
  const count = new Intl.NumberFormat('ko-KR');
  const clock = new Intl.DateTimeFormat('ko-KR', {
    dateStyle: 'short', timeStyle: 'medium', timeZone: 'Asia/Seoul'
  });
  let entries = [];
  try { entries = JSON.parse(sessionStorage.getItem(key) || '[]'); } catch {}

  function save() {
    try { sessionStorage.setItem(key, JSON.stringify(entries)); } catch {}
  }

  function summary(frame) {
    const ranked = [...frame.candidates].sort((a, b) => b.votes - a.votes);
    const [leader, runnerUp] = ranked;
    const time = clock.format(new Date(frame.simulated_at));
    return {
      time,
      leader,
      body: leader.votes === runnerUp.votes
        ? time + ' 가상 집계 기준, ' + ranked.filter(item => item.votes === leader.votes)
          .map(item => item.name).join('·') + ' 후보가 ' + count.format(leader.votes) + '표로 공동 선두다.'
        : time + ' 가상 집계 기준, ' + leader.name + ' 후보가 ' + count.format(leader.votes) +
          '표를 얻어 ' + runnerUp.name + ' 후보에 ' + count.format(leader.votes - runnerUp.votes) + '표 앞섰다.'
    };
  }

  function create(frame, reason, mode) {
    const id = mode + ':' + frame.event_id;
    if (entries.some(entry => entry.id === id)) return false;
    const { time, leader, body } = summary(frame);
    entries.push({
      id, frame, status: 'pending', votes: leader.votes, time, body,
      title: '서울시장 모의 개표 ' + reason + ' · ' + frame.count_progress_pct.toFixed(1) + '%',
      source: '집계 근거 ' + frame.event_id + ' · 후보 근거 ' + leader.row_id
    });
    save();
    return true;
  }

  function valid(entry, votes) {
    return votes === summary(entry.frame).leader.votes;
  }

  function decide(entry, status, note, votes) {
    if (entry.status !== 'pending') return false;
    if (status === 'approved' && !valid(entry, votes)) return false;
    if (status === 'rejected' && !note) return false;
    entry.status = status;
    entry.note = note;
    save();
    return true;
  }

  function list() {
    try {
      const stored = sessionStorage.getItem(key);
      if (stored) entries = JSON.parse(stored);
    } catch {}
    return entries;
  }

  return { create, decide, list, valid };
})();
