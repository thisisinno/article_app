"use client";
import { use, useEffect, useRef, useState } from "react";
import Link from "next/link";
import {useSearchParams} from "next/navigation";
import { api } from "@/lib/api";
import { isActiveRequest, isRequestCancellation } from "@/lib/request-state";
import type {Post} from "@/lib/types";
import {ContentCard} from "@/components/ContentCard";
import {useApp} from "@/components/AppProvider";
import {PostDetailSkeleton} from "@/components/skeletons/Skeletons";
import styles from "./post.module.css";

export default function PostPage({params}:{params:Promise<{postId:string}>}) {
  const id=use(params).postId,search=useSearchParams(),{openComments}=useApp(),[post,setPost]=useState<Post|null>(null),[loading,setLoading]=useState(true),[error,setError]=useState(""),[retry,setRetry]=useState(0),requestSequence=useRef(0);
  useEffect(() => {
    const controller = new AbortController();
    const requestId = ++requestSequence.current;
    setPost(null);
    setError("");
    setLoading(true);
    api<Post>(`/posts/${id}/`, { signal: controller.signal })
      .then((value) => {
        if (isActiveRequest(requestId, requestSequence.current, controller.signal))
          setPost(value);
      })
      .catch((x) => {
        if (
          !isActiveRequest(requestId, requestSequence.current, controller.signal) ||
          isRequestCancellation(x, controller.signal)
        ) return;
        setError(x instanceof Error ? x.message : "Unable to load post.");
      })
      .finally(() => {
        if (isActiveRequest(requestId, requestSequence.current, controller.signal))
          setLoading(false);
      });
    return () => {
      requestSequence.current += 1;
      controller.abort();
    };
  }, [id, retry]);
  useEffect(()=>{if(!post)return;if(search.get("comments")==="1"||location.hash==="#replies")openComments({postId:post.id,postAuthor:post.author,commentCount:post.counts.comments,focusCommentId:search.get("comment")})},[post,search,openComments]);
  if(loading)return <div className="content"><PostDetailSkeleton/></div>;
  if(!post)return <div className="error"><p>{error}</p><button className="secondary" onClick={()=>setRetry(x=>x+1)}>Retry</button></div>;
  return <div className="content"><header className={styles.back}><Link href="/">←</Link><b>Post</b></header><ContentCard initial={post} detail/>{post.thread?.map(item=><ContentCard key={item.id} initial={item} detail/>)}<button className="secondary" onClick={e=>openComments({postId:post.id,postAuthor:post.author,commentCount:post.counts.comments,opener:e.currentTarget})}>View replies · {post.counts.comments}</button></div>;
}
