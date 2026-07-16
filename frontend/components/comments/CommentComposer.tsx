"use client";
import {useEffect,useRef,useState} from "react";
import {api} from "@/lib/api";
import type {Comment} from "@/lib/types";
import {Avatar} from "../Avatar";
import {useApp} from "../AppProvider";
import styles from "./CommentsSheet.module.css";

export function CommentComposer({postId,onCreated}:{postId:string;onCreated:(comment:Comment,count:number)=>void}) {
  const {user}=useApp(),key=`jesca-comment-draft:${postId}`,[body,setBody]=useState(""),[guest,setGuest]=useState(""),[busy,setBusy]=useState(false),[error,setError]=useState(""),area=useRef<HTMLTextAreaElement>(null);
  useEffect(()=>{setBody(localStorage.getItem(key)||"");setGuest(localStorage.getItem("jesca-comment-guest-name")||"")},[key]);
  useEffect(()=>{localStorage.setItem(key,body)},[key,body]);
  useEffect(()=>{if(area.current){area.current.style.height="auto";area.current.style.height=`${Math.min(area.current.scrollHeight,140)}px`}},[body]);
  async function submit(){if(busy||!body.trim()||(!user&&!guest.trim()))return;setBusy(true);setError("");try{const value=await api<{comment:Comment;post_comment_count:number}>(`/posts/${postId}/comments/`,{method:"POST",body:JSON.stringify({body,guest_name:guest})});if(!value?.comment||typeof value.post_comment_count!=="number")throw Error("The server returned an invalid comment response.");localStorage.removeItem(key);if(!user)localStorage.setItem("jesca-comment-guest-name",guest);setBody("");onCreated(value.comment,value.post_comment_count);dispatchEvent(new Event("jesca:notifications-changed"))}catch(x){setError(x instanceof Error?x.message:"Reply could not be posted.")}finally{setBusy(false)}}
  return <div className={styles.composer}>{user?<Avatar user={user} size={36}/>:<span className="avatarFallback">?</span>}<div>{!user&&<input value={guest} onChange={e=>setGuest(e.target.value)} placeholder="Guest display name" aria-label="Guest display name"/>}<textarea ref={area} value={body} onChange={e=>setBody(e.target.value)} placeholder="Post your reply" aria-label="Post your reply" maxLength={2000} rows={1}/><footer><span>{body.length>1750?`${body.length}/2000`:""}</span><button className="primary" disabled={busy||!body.trim()||(!user&&!guest.trim())} onClick={()=>void submit()}>{busy?"Replying…":"Reply"}</button></footer>{error&&<p className="formError" role="alert">{error}</p>}</div></div>;
}

