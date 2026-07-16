"use client";
import {useRef,useState} from "react";
import {api} from "@/lib/api";
import {copyShareLink,openShareWindow} from "@/lib/share";
import {FacebookIcon,InstagramIcon,LinkIcon,MoreShareIcon,WhatsAppIcon,XIcon} from "../Icons";
import {BottomSheet} from "./BottomSheet";
import styles from "./ShareSheet.module.css";
export type ShareTarget={postId:string;title:string;text:string;url:string;onCount?:(count:number)=>void};
export function ShareSheet({target,onClose}:{target:ShareTarget|null;onClose:()=>void}){
  const [feedback,setFeedback]=useState(""),lock=useRef(false);
  if(!target)return null;
  const supportsNative="share" in navigator;
  const record=async(channel:string)=>{if(lock.current)return;lock.current=true;try{const value=await api<{count:number}>(`/posts/${target.postId}/share/`,{method:"POST",body:JSON.stringify({channel})});target.onCount?.(value.count)}finally{setTimeout(()=>{lock.current=false},700)}};
  const popup=(channel:string,url:string)=>openShareWindow(url)?void record(channel):setFeedback("Your browser blocked the share window.");
  const copy=async(message="Link copied",channel="copy")=>{try{await copyShareLink(target.url);setFeedback(message);await record(channel)}catch{setFeedback("Link could not be copied.")}};
  const native=async(channel="native")=>{if(!supportsNative){await copy();return}try{await navigator.share({title:target.title,text:target.text,url:target.url});setFeedback("Shared");await record(channel)}catch(error){if(!(error instanceof DOMException&&error.name==="AbortError"))setFeedback("Sharing was not completed.")}};
  const actions=[
    {label:"WhatsApp",icon:<WhatsAppIcon/>,run:()=>popup("whatsapp",`https://wa.me/?text=${encodeURIComponent(`${target.text} ${target.url}`)}`)},
    {label:"Facebook",icon:<FacebookIcon/>,run:()=>popup("facebook",`https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(target.url)}`)},
    {label:"X",icon:<XIcon/>,run:()=>popup("x",`https://twitter.com/intent/tweet?text=${encodeURIComponent(target.text)}&url=${encodeURIComponent(target.url)}`)},
    {label:"Instagram",icon:<InstagramIcon/>,run:()=>supportsNative?native("instagram_native"):copy("Link copied. Paste it into Instagram.")},
    {label:"Copy link",icon:<LinkIcon/>,run:()=>copy()},
    {label:"More",icon:<MoreShareIcon/>,run:()=>native()},
  ];
  return <BottomSheet open title="Share post" onClose={onClose}><div className={styles.grid}>{actions.filter(x=>x.label!=="More"||supportsNative).map(action=><button key={action.label} className={styles.action} onClick={()=>void action.run()}><span className={styles.icon}>{action.icon}</span><span>{action.label}</span></button>)}</div><p className={styles.feedback} role="status">{feedback}</p></BottomSheet>
}
