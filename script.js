document.addEventListener('DOMContentLoaded', () => {
  window.PUB_USER = null;

  const outside = document.getElementById('view-outside');
  const inside = document.getElementById('view-inside');
  const enterBtn = document.getElementById('enter-btn');

  // Initial state
  outside.style.display = 'flex';
  outside.classList.add('active');
  outside.style.opacity = '1';

  inside.style.display = 'none';
  inside.classList.remove('active');
  inside.style.opacity = '0';

  document.querySelectorAll('.game-screen').forEach(s => {
    s.style.display = 'none';
    s.classList.remove('visible');
    s.style.opacity = '0';
  });

  // Telegram init
  if (window.Telegram?.WebApp) {
    Telegram.WebApp.ready();
    Telegram.WebApp.expand();
  }

  // ===============================
  // ENTER PUB (ONE TIME)
  // ===============================
  enterBtn.addEventListener('click', () => {
    if (!window.Telegram?.WebApp) {
      alert("This only works inside Telegram.");
      return;
    }

    Telegram.WebApp.sendData(JSON.stringify({
      action: "enter_pub"
    }));
  });

  // ===============================
  // SHOW GAME
  // ===============================
  window.showGame = function (gameId) {
    if (!window.PUB_USER) {
      alert("Enter the pub first.");
      return;
    }

    inside.style.opacity = '0';
    setTimeout(() => {
      inside.style.display = 'none';
      inside.classList.remove('active');

      const screen = document.getElementById('game-' + gameId);
      if (!screen) return;

      screen.style.display = 'block';
      screen.classList.add('visible');
      screen.style.opacity = '1';

      if (gameId === 'football') loadFootballCard();
    }, 800);
  };

  window.backToPub = function () {
    document.querySelectorAll('.game-screen').forEach(s => {
      s.style.opacity = '0';
    });

    setTimeout(() => {
      document.querySelectorAll('.game-screen').forEach(s => {
        s.style.display = 'none';
        s.classList.remove('visible');
      });

      inside.style.display = 'flex';
      inside.classList.add('active');
      inside.style.opacity = '1';
    }, 800);
  };

  // ===============================
  // FOOTBALL CARD
  // ===============================
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
    if (!grid) return;

    grid.innerHTML = '';

    footballTeams.forEach(team => {
      const slot = document.createElement('div');
      slot.className = 'team-slot';
      slot.innerHTML = `
        <div class="team-name">${team}</div>
        <div class="username">[Pick Me]</div>
      `;
      slot.onclick = () => pickTeam(team, slot);
      grid.appendChild(slot);
    });

    requestCardState();
  }

  function pickTeam(team, slot) {
    const user = Telegram.WebApp.initDataUnsafe?.user;
    if (!user?.username) {
      alert("Set a Telegram username first.");
      return;
    }

    if (!confirm(`Claim ${team} for $1 USDC as @${user.username}?`)) return;

    slot.style.opacity = '0.6';
    slot.querySelector('.username').textContent = 'Processing...';
    slot.style.pointerEvents = 'none';

    Telegram.WebApp.sendData(JSON.stringify({
      action: 'pickteam_web',
      team
    }));

    setTimeout(requestCardState, 2000);
  }

  function requestCardState() {
    Telegram.WebApp.sendData(JSON.stringify({
      action: 'get_card_state'
    }));
  }

  function updateGrid(claims) {
    document.querySelectorAll('.team-slot').forEach(slot => {
      const team = slot.querySelector('.team-name').textContent.trim();
      const claimed = claims[team];

      if (claimed) {
        slot.querySelector('.username').textContent = claimed;
        slot.classList.add('claimed');
        slot.style.pointerEvents = 'none';
      } else {
        slot.querySelector('.username').textContent = '[Pick Me]';
        slot.style.pointerEvents = 'auto';
      }
      slot.style.opacity = '1';
    });
  }

  // ===============================
  // BOT RESPONSES
  // ===============================
  Telegram.WebApp.onEvent('web_app_data', event => {
    if (typeof event.data !== 'string') return;

    if (event.data.startsWith("ENTER_OK:")) {
      const payload = JSON.parse(event.data.replace("ENTER_OK:", ""));
      window.PUB_USER = payload;

      outside.style.opacity = '0';
      setTimeout(() => {
        outside.style.display = 'none';
        outside.classList.remove('active');

        inside.style.display = 'flex';
        inside.classList.add('active');
        inside.style.opacity = '1';
      }, 800);
      return;
    }

    if (event.data === "ENTER_DENIED:NO_USERNAME") {
      alert("Set a Telegram username first.");
      return;
    }

    if (event.data === "ENTER_DENIED:NO_WALLET") {
      alert("No wallet found. DM the bot with /start.");
      return;
    }

    if (event.data.startsWith("CARD_STATE:")) {
      const state = JSON.parse(event.data.replace("CARD_STATE:", ""));
      updateGrid(state);
    }
  });
});
