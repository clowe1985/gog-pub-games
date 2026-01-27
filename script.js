document.addEventListener('DOMContentLoaded', () => {
  const outside = document.getElementById('view-outside');
  const inside = document.getElementById('view-inside');
  const enterBtn = document.getElementById('enter-btn');

  // Force proper start: outside view only
  outside.style.display = 'flex';
  outside.classList.add('active');
  outside.style.opacity = '1';
  inside.style.display = 'none';
  inside.classList.remove('active');
  inside.style.opacity = '0';

  // Hide all game screens
  document.querySelectorAll('.game-screen').forEach(screen => {
    screen.style.display = 'none';
    screen.classList.remove('visible');
  });

  // Enter pub button
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

  // Telegram init
  if (window.Telegram?.WebApp) {
    Telegram.WebApp.ready();
    Telegram.WebApp.expand();
  }

  // Show game tab
  window.showGame = function(gameId) {
    const pub = document.getElementById('view-inside');
    pub.style.opacity = '0';

    setTimeout(() => {
      pub.style.display = 'none';
      pub.classList.remove('active');

      const gameScreen = document.getElementById('game-' + gameId);
      if (!gameScreen) return;

      gameScreen.style.display = 'block';
      gameScreen.classList.add('visible');
      gameScreen.style.opacity = '1';

      // Load football card state when tab opens
      if (gameId === 'football') {
        fetchCardState();
      }
    }, 800);
  };

  // Back to pub
  window.backToPub = function() {
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

  // Football card state fetch
  function fetchCardState() {
    const grid = document.getElementById('football-grid');
    if (!grid) {
      console.error("football-grid missing!");
      return;
    }

    // Ask bot for state
    Telegram.WebApp.sendData(JSON.stringify({ action: "get_card_state" }));
    console.log("Requested card state from bot");

    const handler = (event) => {
      console.log("Bot reply:", event.data);
      if (event.data.startsWith("CARD_STATE:")) {
        try {
          const payload = JSON.parse(event.data.replace("CARD_STATE:", ""));
          renderFootballGrid(payload.teams || {});
        } catch (e) {
          console.error("Failed to parse card state:", e);
        }
        Telegram.WebApp.offEvent('message', handler);
      }
    };

    Telegram.WebApp.onEvent('message', handler);

    // Timeout fallback
    setTimeout(() => {
      Telegram.WebApp.offEvent('message', handler);
      console.log("Card state request timed out");
    }, 5000);
  }

  // Render grid from bot state
  function renderFootballGrid(state) {
    const grid = document.getElementById('football-grid');
    if (!grid) return;

    grid.innerHTML = '';

    footballTeams.forEach(team => {
      const claimedBy = state[team] || '[Pick Me]';
      const slot = document.createElement('div');
      slot.className = 'team-slot' + (claimedBy !== '[Pick Me]' ? ' claimed' : '');
      slot.innerHTML = `
        <div>${team}</div>
        <div class="username">${claimedBy}</div>
      `;

      if (claimedBy === '[Pick Me]') {
        slot.onclick = () => claimTeam(team, slot);
      }

      grid.appendChild(slot);
    });
  }

  // Claim team
  function claimTeam(team, slot) {
    const user = Telegram.WebApp.initDataUnsafe.user;
    if (!user || !user.username) {
      alert("No username? Can't claim.");
      return;
    }

    const username = '@' + user.username;

    if (!confirm(`Claim ${team} for $1 as ${username}?`)) return;

    Telegram.WebApp.sendData(JSON.stringify({
      action: "claim_team",
      team: team,
      username: username
    }));

    const handler = (event) => {
      console.log("Claim reply:", event.data);
      if (event.data === "CLAIM_SUCCESS") {
        slot.querySelector('.username').textContent = username;
        slot.classList.add('claimed');
        slot.onclick = null;
      } else if (event.data.startsWith("CLAIM_DENIED")) {
        alert(event.data.replace("CLAIM_DENIED:", "").trim());
      }
      Telegram.WebApp.offEvent('message', handler);
    };

    Telegram.WebApp.onEvent('message', handler);

    setTimeout(() => {
      Telegram.WebApp.offEvent('message', handler);
    }, 5000);
  }

  // Football teams list
  const footballTeams = [
    "Arsenal", "Ajax", "Bournemouth", "Brentford", "Brighton", "Burnley",
    "Chelsea", "Crystal Palace", "Everton", "Fulham", "Liverpool", "Luton",
    "Man City", "Man United", "Newcastle", "Nottingham Forest", "Sheffield Utd",
    "Tottenham", "West Ham", "Wolves", "Leicester", "Leeds", "Southampton",
    "Blackburn", "Birmingham", "Coventry", "Ipswich", "Middlesbrough", "Norwich",
    "Preston", "QPR", "Sheffield Wed"
  ];
});
