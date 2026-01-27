document.addEventListener('DOMContentLoaded', () => {
  const outside = document.getElementById('view-outside');
  const inside = document.getElementById('view-inside');
  const enterBtn = document.getElementById('enter-btn');

  outside.style.display = 'flex';
  inside.style.display = 'none';

  enterBtn.addEventListener('click', () => {
    outside.style.display = 'none';
    inside.style.display = 'flex';
  });

  if (window.Telegram?.WebApp) {
    Telegram.WebApp.ready();
    Telegram.WebApp.expand();
  }

  window.showGame = function (gameId) {
    document.querySelectorAll('.game-screen').forEach(g => g.style.display = 'none');

    const game = document.getElementById('game-' + gameId);
    if (!game) return;

    game.style.display = 'block';

    if (gameId === 'football') {
      loadFootballCard();
    }
  };

  window.backToPub = function () {
    document.querySelectorAll('.game-screen').forEach(g => g.style.display = 'none');
    inside.style.display = 'flex';
  };

  const footballTeams = [
    "Arsenal","Ajax","Bournemouth","Brentford","Brighton","Burnley",
    "Chelsea","Crystal Palace","Everton","Fulham","Liverpool","Luton",
    "Man City","Man United","Newcastle","Nottingham Forest","Sheffield Utd",
    "Tottenham","West Ham","Wolves","Leicester","Leeds","Southampton",
    "Blackburn","Birmingham","Coventry","Ipswich","Middlesbrough","Norwich",
    "Preston","QPR","Sheffield Wed"
  ];

  function loadFootballCard() {
    const grid = document.getElementById('football-grid');
    if (!grid) {
      console.error("football-grid missing");
      return;
    }

    Telegram.WebApp.sendData(JSON.stringify({ action: "get_card_state" }));

    const handler = (event) => {
      if (!event.data.startsWith("CARD_STATE:")) return;

      const payload = JSON.parse(event.data.replace("CARD_STATE:", ""));
      renderFootballGrid(payload.teams || {});
      Telegram.WebApp.offEvent('message', handler);
    };

    Telegram.WebApp.onEvent('message', handler);
  }

  function renderFootballGrid(state) {
    const grid = document.getElementById('football-grid');
    grid.innerHTML = '';

    footballTeams.forEach(team => {
      const claimedBy = state[team] || '[Pick Me]';

      const slot = document.createElement('div');
      slot.className = 'team-slot' + (claimedBy !== '[Pick Me]' ? ' claimed' : '');
      slot.innerHTML = `<div>${team}</div><div class="username">${claimedBy}</div>`;

      if (claimedBy === '[Pick Me]') {
        slot.onclick = () => claimTeam(team, slot);
      }

      grid.appendChild(slot);
    });
  }

  function claimTeam(team, slot) {
    const user = Telegram.WebApp.initDataUnsafe.user;
    if (!user?.username) return;

    const username = '@' + user.username;

    Telegram.WebApp.sendData(JSON.stringify({
      action: "claim_team",
      team,
      username
    }));

    const handler = (event) => {
      if (event.data === "CLAIM_SUCCESS") {
        slot.querySelector('.username').textContent = username;
        slot.classList.add('claimed');
        slot.onclick = null;
      }
      Telegram.WebApp.offEvent('message', handler);
    };

    Telegram.WebApp.onEvent('message', handler);
  }
});
