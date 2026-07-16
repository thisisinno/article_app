export const getPostShareUrl=(postId:string)=>typeof window==="undefined"?`/post/${postId}`:new URL(`/post/${postId}`,window.location.origin).toString();
export const getPostShareText=(title:string,text:string)=>(title||text.replace(/\s+/g," ").trim().slice(0,180)||"Jesca Social Work");
export const openShareWindow=(url:string)=>Boolean(window.open(url,"_blank","noopener,noreferrer,width=720,height=680"));
export async function copyShareLink(url:string){if(navigator.clipboard?.writeText){await navigator.clipboard.writeText(url);return}const input=document.createElement("input");input.value=url;input.style.position="fixed";input.style.opacity="0";document.body.appendChild(input);input.select();const ok=document.execCommand("copy");input.remove();if(!ok)throw Error("copy_failed")}
