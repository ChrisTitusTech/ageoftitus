async function handleRequest(request, env) {
  const url = new URL(request.url);
  console.log("Received request for:", url.pathname);

  if (url.pathname === '/api/check-status') {
    return await checkStatus(request, env);
  }
  
  if (url.pathname === '/api/' || url.pathname === '/api') {
    return new Response('Welcome to the Twitch status checker API!', {
      headers: { 'Content-Type': 'text/plain' }
    });
  }
  
  return new Response(`Not Found: ${url.pathname}`, { 
    status: 404,
    headers: { 'Content-Type': 'text/plain' }
  });
}

async function checkStatus(request, env) {
  if (typeof env?.TWITCH_KV === 'undefined') {
    console.error('TWITCH_KV is not defined');
    return new Response('Configuration error: TWITCH_KV not available', { status: 500 });
  }

  try {
    let token = await env.TWITCH_KV.get('access_token')
    if (!token) {
      console.log("No existing token found, generating new one")
      token = await generateNewToken(env)
      await env.TWITCH_KV.put('access_token', token, {expirationTtl: 30 * 24 * 60 * 60}) // 30 days
    } else {
      console.log("Using existing token")
    }
    
    const status = await checkChannelStatus(token, env)
    
    return new Response(JSON.stringify(status), {
      headers: { 'Content-Type': 'application/json' }
    })
  } catch (error) {
    console.error("Error in checkStatus:", error)
    return new Response(`Error checking status: ${error.message}`, { status: 500 })
  }
}

async function generateNewToken(env) {
  const clientId = env.CLIENT_ID
  const clientSecret = env.CLIENT_SECRET
  
  console.log("Generating new token with Client ID:", clientId.substring(0, 5) + "...")

  const response = await fetch('https://id.twitch.tv/oauth2/token', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
    },
    body: new URLSearchParams({
      client_id: clientId,
      client_secret: clientSecret,
      grant_type: 'client_credentials',
    }),
  })

  if (!response.ok) {
    console.error("Error generating token. Status:", response.status)
    const text = await response.text()
    console.error("Response:", text)
    throw new Error(`Failed to generate token: ${response.status} ${text}`)
  }

  const data = await response.json()
  return data.access_token
}

async function checkChannelStatus(token, env) {
  const clientId = env.CLIENT_ID;
  const channelName = env.CHANNEL_NAME;

  console.log("Checking channel status for:", channelName)

  const response = await fetch(`https://api.twitch.tv/helix/streams?user_login=${channelName}`, {
    headers: {
      'Client-ID': clientId,
      'Authorization': `Bearer ${token}`,
    },
  })

  if (!response.ok) {
    console.error("Error checking channel status. Status:", response.status)
    const text = await response.text()
    console.error("Response:", text)
    throw new Error(`Failed to check channel status: ${response.status} ${text}`)
  }

  const data = await response.json()
  return {
    isLive: data.data.length > 0,
    viewerCount: data.data.length > 0 ? data.data[0].viewer_count : 0,
  }
}

export default {
  async fetch(request, env, ctx) {
    try {
      return await handleRequest(request, env);
    } catch (error) {
      console.error("Error in handleRequest:", error);
      return new Response(`Server Error: ${error.message}`, { status: 500 });
    }
  }
};
