document.addEventListener('DOMContentLoaded', () => {
  // Force redeploy 2025-01-29
  console.log(">>> SCRIPT LOADED");

  const outside = document.getElementById('view-outside');
  const inside = document.getElementById('view-inside');
  const enterBtn = document.getElementById('enter-btn');

  outside.style.display = 'flex';
  outside.classList.add('active');
  outside.style.opacity = '1';
  inside.style.display = 'none';
  inside.classList.remove('active');
  inside.style.opacity = '0';

  document.querySelectorAll('.game-screen').forEach(s => {
    s.style.display = 'none';
    s.classList.remove('visible');
  });

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

  if (window.Telegram?.WebApp) {
    Telegram.WebApp.ready();
    Telegram.WebApp.expand();
  }

  window.showGame = function(gameId) {
    inside.style.opacity = '0';
    setTimeout(() => {
      inside.style.display = 'none';
      inside.classList.remove('active');
      const screen = document.getElementById('game-' + gameId);
      if (!screen) return console.error("Missing screen:", gameId);
      screen.style.display = 'block';
      screen.classList.add('visible');
      screen.style.opacity = '1';
      if (gameId === 'football') loadFootballCard();
    }, 800);
  };

  window.backToPub = function() {
    document.querySelectorAll('.game-screen').forEach(s => s.style.opacity = '0');
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

  const footballTeams = [
    "Arsenal", "Aston Villa", "Bournemouth", "Brentford", "Brighton", "Burnley",
    "Chelsea", "Crystal Palace", "Everton", "Fulham", "Liverpool", "Luton",
    "Man City", "Man United", "Newcastle", "Nottingham Forest", "Sheffield Utd",
    "Tottenham", "West Ham", "Wolves", "Leicester", "Leeds", "Southampton",
    "Blackburn", "Birmingham", "Coventry", "Ipswich", "Middlesbrough", "Norwich",
    "Preston", "QPR", "Sheffield Wed"
  ];

  function loadFootballCard() {
    const grid = document.getElementById('football-grid');
    if (!grid) return console.error("Grid missing");
    grid.innerHTML = '';
    footballTeams.forEach(team => {
      const slot = document.createElement('div');
      slot.className = 'team-slot';
      slot.innerHTML = `<div class="team-name">${team}</div><div class="username">[Pick Me]</div>`;
      slot.onclick = () => pickTeam(team, slot);
      grid.appendChild(slot);
    });
    console.log("Grid loaded");
    loadSavedClaims();
  }

  function pickTeam(team, slot) {
    const user = Telegram.WebApp.initDataUnsafe.user;
    if (!user || !user.username) {
      alert("No username found.");
      return;
    }
    const username = '@' + user.username;

    if (!confirm(`Claim ${team} for $1 as ${username}?`)) return;

    slot.style.opacity = '0.7';
    slot.querySelector('.username').textContent = 'Processing...';
    slot.style.pointerEvents = 'none';

    try {
      Telegram.WebApp.sendData(JSON.stringify({
        action: "claim_team",
        team: team,
        username: username
      }));
      console.log("Claim sent:", team, username);

      setTimeout(() => {
        Telegram.WebApp.sendData(JSON.stringify({ action: "get_card_state" }));
      }, 1500);
    } catch (err) {
      console.error("Send failed:", err);
      slot.style.opacity = '1';
      slot.querySelector('.username').textContent = '[Pick Me]';
      slot.style.pointerEvents = 'auto';
    }
  }

  async function loadSavedClaims() {
    Telegram.WebApp.sendData(JSON.stringify({ action: "get_card_state" }));
  }

  function updateGrid(claims) {
    document.querySelectorAll('.team-slot').forEach(slot => {
      const team = slot.querySelector('.team-name').textContent.trim();
      const claimed = claims[team];
      if (claimed) {
        slot.querySelector('.username').textContent = claimed;
        slot.classList.add('claimed');
        slot.onclick = null;
        slot.style.opacity = '1';
        slot.style.pointerEvents = 'none';
      } else if (slot.style.opacity === '0.7') {
        slot.style.opacity = '1';
        slot.querySelector('.username').textContent = '[Pick Me]';
        slot.style.pointerEvents = 'auto';
      }
    });
  }

  Telegram.WebApp.onEvent('web_app_data', (event) => {
    const data = event.data;
    if (typeof data !== 'string') return;

    if (data.startsWith("CARD_STATE:")) {
      try {
        const json = data.replace('CARD_STATE:', '');
        const state = JSON.parse(json);
        updateGrid(state.teams || state);
      } catch (e) {
        console.error("State parse error:", e);
      }
    }
  });
});
