document.addEventListener('DOMContentLoaded', () => {
  const outside = document.getElementById('view-outside');
  const inside  = document.getElementById('view-inside');
  const enterBtn = document.getElementById('enter-btn');

  console.log("User:", Telegram.WebApp.initDataUnsafe.user);

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
      if (!screen) {
        console.error("Missing screen:", gameId);
        return;
      }
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
    "Arsenal", "Ajax", "Bournemouth", "Brentford", "Brighton", "Burnley",
    "Chelsea", "Crystal Palace", "Everton", "Fulham", "Liverpool", "Luton",
    "Man City", "Man United", "Newcastle", "Nottingham Forest", "Sheffield Utd",
    "Tottenham", "West Ham", "Wolves", "Leicester", "Leeds", "Southampton",
    "Blackburn", "Birmingham", "Coventry", "Ipswich", "Middlesbrough", "Norwich",
    "Preston", "QPR", "Sheffield Wed"
  ];

  let currentSlot = null;

  function loadFootballCard() {
    const grid = document.getElementById('football-grid');
    if (!grid) {
      console.error("No #football-grid");
      return;
    }
    grid.innerHTML = '';
    footballTeams.forEach(team => {
      const slot = document.createElement('div');
      slot.className = 'team-slot';
      slot.innerHTML = `<div>${team}</div><div class="username">[Pick Me]</div>`;
      slot.onclick = () => pickTeam(team, slot);
      grid.appendChild(slot);
    });
    console.log("Grid built");
    loadExistingClaims();
  }

  async function loadExistingClaims() {
    try {
      Telegram.WebApp.sendData(JSON.stringify({action: "get_card_state"}));
    } catch (e) {
      console.error("State request failed:", e);
    }
  }

  function updateGridWithClaims(claims) {
    const slots = document.querySelectorAll('.team-slot');
    slots.forEach(slot => {
      const team = slot.querySelector('div:first-child').textContent.trim();
      const claimedBy = claims[team];
      if (claimedBy) {
        slot.querySelector('.username').textContent = claimedBy;
        slot.classList.add('claimed');
        slot.onclick = null;
      }
    });
  }

  function pickTeam(team, slot) {
    const user = Telegram.WebApp.initDataUnsafe.user;
    if (!user || !user.username) {
      alert("No username — can't claim.");
      return;
    }
    const username = '@' + user.username;
    if (!confirm(`Claim ${team} for $1 as ${username}?`)) return;
    currentSlot = slot;
    Telegram.WebApp.sendData(JSON.stringify({
      action: "claim_team",
      team: team,
      username: username
    }));
    console.log(`Claim sent: ${team} → ${username}`);
  }

  Telegram.WebApp.onEvent('web_app_data', (event) => {
    const data = event.data;
    if (!data || typeof data !== 'string') return;

    if (data.startsWith('CARD_STATE:')) {
      const json = data.replace('CARD_STATE:', '');
      try {
        const state = JSON.parse(json);
        updateGridWithClaims(state.teams || state);
      } catch (e) {
        console.error("Bad state:", e);
      }
    } else if (data.startsWith('CLAIM_') && currentSlot) {
      if (data === 'CLAIM_SUCCESS') {
        const username = '@' + Telegram.WebApp.initDataUnsafe.user.username;
        currentSlot.querySelector('.username').textContent = username;
        currentSlot.classList.add('claimed');
        currentSlot.onclick = null;
        alert('Claimed! 🎉');
        currentSlot = null;
      } else {
        const reason = data.split(':')[1]?.trim() || 'Error';
        alert('Failed: ' + reason);
        currentSlot = null;
      }
    }
  });
});
