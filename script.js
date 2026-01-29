document.addEventListener('DOMContentLoaded', () => {
  console.log(">>> SCRIPT LOADED");

  const outside = document.getElementById('view-outside');
  const inside = document.getElementById('view-inside');
  const enterBtn = document.getElementById('enter-btn');

  outside.style.display = 'flex';
  outside.style.opacity = '1';
  inside.style.display = 'none';

  document.querySelectorAll('.game-screen').forEach(s => {
    s.style.display = 'none';
  });

  enterBtn.addEventListener('click', () => {
    outside.style.opacity = '0';
    setTimeout(() => {
      outside.style.display = 'none';
      inside.style.display = 'flex';
      inside.style.opacity = '1';
    }, 1200);
  });

  if (window.Telegram?.WebApp) {
    Telegram.WebApp.ready();
    Telegram.WebApp.expand();
  }

  window.showGame = function (gameId) {
    inside.style.opacity = '0';
    setTimeout(() => {
      inside.style.display = 'none';
      const screen = document.getElementById('game-' + gameId);
      if (!screen) return console.error("Missing screen:", gameId);
      screen.style.display = 'block';
      screen.style.opacity = '1';
      if (gameId === 'football') loadFootballCard();
    }, 800);
  };

  window.backToPub = function () {
    document.querySelectorAll('.game-screen').forEach(s => {
      s.style.opacity = '0';
      setTimeout(() => {
        s.style.display = 'none';
      }, 800);
    });
    setTimeout(() => {
      inside.style.display = 'flex';
      inside.style.opacity = '1';
    }, 800);
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
    if (!grid) return console.error("Grid missing");

    grid.innerHTML = '';

    footballTeams.forEach(team => {
      const slot = document.createElement('div');
      slot.className = 'team-slot';
      slot.innerHTML = `
        <div class="team-name">${team}</div>
        <div class="username">[Pick Me]</div>
      `;
      slot.addEventListener('click', () => pickTeam(team));
      grid.appendChild(slot);
    });

    requestCardState();
  }

  function pickTeam(team) {
    const user = Telegram.WebApp.initDataUnsafe?.user;
    if (!user || !user.username) {
      alert("No Telegram username found.");
      return;
    }

    const username = '@' + user.username;

    if (!confirm(`Claim ${team} for $1 as ${username}?`)) return;

    Telegram.WebApp.sendData(JSON.stringify({
      action: "claim_team",
      team: team,
      username: username
    }));
  }

  function requestCardState() {
    Telegram.WebApp.sendData(JSON.stringify({
      action: "get_card_state"
    }));
  }

  function updateGrid(teams) {
    console.log("Applying claims:", teams);

    document.querySelectorAll('.team-slot').forEach(slot => {
      const team = slot.querySelector('.team-name').textContent.trim();
      const username = teams[team];

      const userEl = slot.querySelector('.username');

      if (username) {
        userEl.textContent = username;
        slot.classList.add('claimed');
        slot.style.pointerEvents = 'none';
      } else {
        userEl.textContent = '[Pick Me]';
        slot.classList.remove('claimed');
        slot.style.pointerEvents = 'auto';
      }
    });
  }

  Telegram.WebApp.onEvent('web_app_data', (event) => {
    const data = event.data;
    if (typeof data !== 'string') return;

    if (!data.startsWith("CARD_STATE:")) return;

    try {
      const payload = JSON.parse(data.replace("CARD_STATE:", ""));
      if (!payload.teams || typeof payload.teams !== 'object') {
        console.error("Invalid state shape:", payload);
        return;
      }
      updateGrid(payload.teams);
    } catch (e) {
      console.error("CARD_STATE parse failed:", e);
    }
  });
});
