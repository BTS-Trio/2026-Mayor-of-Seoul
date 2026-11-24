const VoteDrafts = (() => {
  const key = 'seoul-vote-drafts';
  const seenKey = key + ':seen';
  const count = new Intl.NumberFormat('ko-KR');
  const clock = new Intl.DateTimeFormat('ko-KR', {
    dateStyle: 'short', timeStyle: 'medium', timeZone: 'Asia/Seoul'
  });
  let entries = [];
  try { entries = JSON.parse(localStorage.getItem(key) || sessionStorage.getItem(key) || '[]'); } catch {}
  let seen = [];
  try { seen = JSON.parse(localStorage.getItem(seenKey) || '[]'); } catch {}

  function save() {
    try { localStorage.setItem(key, JSON.stringify(entries)); } catch {}
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
    list();
    const eventKey = mode + ':' + frame.event_id;
    const id = eventKey + ':' + reason;
    if (entries.some(entry => entry.id === id ||
      (entry.id === eventKey && (entry.title.includes(reason) ||
        (reason === '50% 도달' && entry.title.includes('중간 집계')))))) return false;
    const { time, leader, body } = summary(frame);
    entries.push({
      id, frame, reason, status: 'pending', votes: leader.votes, time, body,
      kind: reason === '선두 변경' ? 'followup' : 'count',
      title: '서울시장 모의 개표 ' + reason + ' · ' + frame.count_progress_pct.toFixed(1) + '%',
      source: '집계 근거 ' + frame.event_id + ' · 후보 근거 ' + leader.row_id
    });
    save();
    return true;
  }

  function valid(entry, votes) {
    return votes === summary(entry.frame).leader.votes;
  }

  function decide(id, status, note, votes) {
    const entry = list().find(item => item.id === id);
    if (entry?.status !== 'pending') return false;
    if (status === 'approved' && !valid(entry, votes)) return false;
    if (status === 'rejected' && !note) return false;
    entry.status = status;
    entry.note = note;
    entry.decidedAt = Date.now();
    save();
    return true;
  }

  function list() {
    try {
      const stored = localStorage.getItem(key);
      if (stored) entries = JSON.parse(stored);
    } catch {}
    return entries;
  }

  function unread() {
    try { seen = JSON.parse(localStorage.getItem(seenKey) || '[]'); } catch {}
    return list().filter(entry => !seen.includes(entry.id)).length;
  }

  function markSeen() {
    seen = list().map(entry => entry.id);
    try { localStorage.setItem(seenKey, JSON.stringify(seen)); } catch {}
  }

  function approved(entries = list()) {
    return entries.filter(entry => entry.status === 'approved')
      .sort((a, b) => (b.decidedAt || 0) - (a.decidedAt || 0));
  }

  function markPublished(id) {
    const entry = list().find(item => item.id === id);
    if (entry) {
      entry.published = true;
      save();
    }
  }

  return { approved, create, decide, list, markPublished, markSeen, unread, valid };
})();
