async function checkLiveStatus() {
  const twitchContainerElement = document.getElementById('twitch-container');
  const twitchEmbedElement = document.getElementById('twitch-embed');
  const statusBannerElement = document.getElementById('twitch-status-banner');
  
  if (!twitchContainerElement || !twitchEmbedElement || !statusBannerElement) {
    console.error('Twitch elements not found');
    return;
  }

  console.log('Checking live status...');
  try {
    const response = await fetch('https://ageoftitus.com/api/check-status', {
      credentials: 'same-origin'
    });
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    const data = await response.json();
    console.log('Response from worker:', data);

    if (data.isLive) {
      console.log(`Channel ${data.channelName} is live, updating embed`);
      const embedSrc = `https://player.twitch.tv/?channel=${data.channelName}&parent=${window.location.hostname}`;
      console.log('Embed source:', embedSrc);
      twitchEmbedElement.innerHTML = `
        <iframe
          src="${embedSrc}"
          height="480"
          width="100%"
          allowfullscreen>
        </iframe>
      `;
      statusBannerElement.innerHTML = `<h2>🔴 Live on Twitch</h2>`;
      twitchEmbedElement.style.display = 'block';
    } else {
      console.log(`Channel ${data.channelName} is offline, clearing embed`);
      twitchEmbedElement.innerHTML = '';
      twitchEmbedElement.style.display = 'none';
      const lastOnline = data.lastOnline ? new Date(data.lastOnline).toLocaleString() : 'Unknown';
      statusBannerElement.innerHTML = `<h2>⚫ Offline on Twitch</h2><p>Last online: ${lastOnline}</p>`;
    }
    
    // Always show the container and status banner
    twitchContainerElement.style.display = 'block';
    statusBannerElement.style.display = 'block';
  } catch (error) {
    console.error('Error checking Twitch live status:', error);
    statusBannerElement.innerHTML = `<h2>⚠️ Unable to check stream status</h2>`;
    twitchContainerElement.style.display = 'block';
    statusBannerElement.style.display = 'block';
  }
}

// Check live status when the page loads
document.addEventListener('DOMContentLoaded', checkLiveStatus);

// Check live status every 5 minutes
setInterval(checkLiveStatus, 5 * 60 * 1000);
