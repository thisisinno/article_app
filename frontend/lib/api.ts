const BASE=process.env.NEXT_PUBLIC_API_URL||"/api/v1";
let csrf="";
async function token(){if(!csrf){const r=await fetch(`${BASE}/auth/csrf/`,{credentials:"include"});csrf=(await r.json()).csrfToken}return csrf}
export async function api<T>(path:string,init:RequestInit={}):Promise<T>{
 const method=init.method?.toUpperCase()||"GET";const headers=new Headers(init.headers);
 if(init.body&&!headers.has("Content-Type"))headers.set("Content-Type","application/json");
 if(!["GET","HEAD","OPTIONS"].includes(method))headers.set("X-CSRFToken",await token());
 const r=await fetch(`${BASE}${path}`,{...init,headers,credentials:"include",cache:"no-store"});
 if(!r.ok){let message=`Request failed (${r.status})`;try{message=(await r.json()).error?.message||message}catch{}throw new Error(message)}
 return (r.status===204?{}:await r.json()) as T;
}
