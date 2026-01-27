document.addEventListener('DOMContentLoaded', () => {
  const outside = document.getElementById('view-outside');
  const inside = document.getElementById('view-inside');
  const enterBtn = document.getElementById('enter-btn');

  let currentCardState = {};

  // ---------- FORCE SAFE START ----------
  outside.style.display = 'flex';
  outside.classList.add('active');
  outside.style.opacity = '1';

  inside.style.display = 'none';
  inside.classList.remove('active');
  inside.style.opacity = '0';

  document.querySelectorAll('.game-screen').forEach(screen => {
    screen.style.display = 'none';
    screen.classList.remove('visible');
    screen.style.opacity = '0';
  });

  // ---------- TELEGRAM INIT ----------
  if (window.Telegram?.WebApp) {
    Telegram.WebApp.ready();
    Telegram.WebApp.expand();
  }

  // ---------- ENTER PUB ----------
  enterBtn.addEventListener('click', () => {
    outside.style.opacity = '0';
    setTimeout(() => {
      outside.style.display = 'none';
      outside.classList.remove('active');

      inside.style.display = 'flex';
      inside.classList.add('active');
      inside.style.opacity = '1';
    }, 1200);
  });

  // ---------- GLOBAL BOT MESSAGE HANDLER ----------
  Telegram.WebApp.onEvent('message', (event) => {
    if (!event.data) return;

    // CARD STATE
    if (event.data.startsWith('CARD_STATE:')) {
      try {
        const payload = JSON.parse(event.data.replace('CARD_STATE:', ''));
        currentCardState = payload.teams || {};
        renderFootballGrid();
      } catch (e) {
        console.error('Failed to parse card state', e);
      }
      return;
    }

    // CLAIM RESULT
    if (event.data === 'CLAIM_SUCCESS') {
      requestCardState();
      return;
    }

    if (event.data.startsWith('CLAIM_DENIED')) {
      alert(event.data.replace('CLAIM_DENIED:', '').trim());
      return;
    }
  });

  // ---------- GAME NAV ----------
  window.showGame = function (gameId) {
    inside.style.opacity = '0';

    setTimeout(() => {
      inside.style.display = 'none';
      inside.classList.remove('active');

      const game = document.getElementById('game-' + gameId);
      game.style.display = 'block';
      game.classList.add('visible');
      game.style.opacity = '1';

      if (gameId === 'football') {
        requestCardState();
      }
    }, 800);
  };

  window.backToPub = function () {
    document.querySelectorAll('.game-screen').forEach(screen => {
      screen.style.opacity = '0';
    });

    setTimeout(() => {
      document.querySelectorAll('.game-screen').forEach(screen => {
        screen.style.display = 'none';
        screen.classList.remove('visible');
      });

      inside.style.display = 'flex';
      inside.classList.add('active');
      inside.style.opacity = '1';
    }, 800);
  };

  // ---------- FOOTBALL CARD ----------
  function requestCardState() {
    Telegram.WebApp.sendData(JSON.stringify({
      action: 'get_card_state'
    }));
  }

  function renderFootballGrid() {
    const grid = document.getElementById('football-grid');
    if (!grid) return;

    grid.innerHTML = '';

    footballTeams.forEach(team => {
      const claimedBy = currentCardState[team] || null;

      const slot = document.createElement('div');
      slot.className = 'team-slot';
      if (claimedBy) slot.classList.add('claimed');

      slot.innerHTML = `
        <div>${team}</div>
        <div class="username">${claimedBy || '[Pick Me]'}</div>
      `;

      if (!claimedBy) {
        slot.onclick = () => attemptClaim(team);
      }

      grid.appendChild(slot);
    });
  }

  function attemptClaim(team) {
    const tgUser = Telegram.WebApp.initDataUnsafe.user;
    if (!tgUser || !tgUser.username) {
      alert('No Telegram username found. Set one first.');
      return;
    }

    const username = '@' + tgUser.username;

    if (!confirm(`Claim ${team} for $1 as ${username}?`)) return;

    Telegram.WebApp.sendData(JSON.stringify({
      action: 'claim_team',
      team: team,
      username: username
    }));
  }
});
