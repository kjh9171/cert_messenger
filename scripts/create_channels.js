const axios = require('axios');

async function create(api, token, count, prefix){
  for(let i=1;i<=count;i++){
    const name = `${prefix}-${i}`;
    const headers = {'Content-Type':'application/json'};
    if(token) headers.Authorization = `Bearer ${token}`;
    try{
      const r = await axios.post(`${api}/api/channels`, { name });
      console.log(r.data.channelLink);
    }catch(e){
      console.error('error', e.response ? e.response.data : e.message);
    }
  }
}

const api = process.argv[2] || 'http://localhost:3100';
const token = process.env.TOKEN || '';
const count = parseInt(process.argv[3] || '5', 10);
const prefix = process.argv[4] || 'auto';
create(api, token, count, prefix);
