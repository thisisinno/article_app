"use client";import{useEffect,useState}from"react";
const absolute=(value:string)=>new Intl.DateTimeFormat("en",{month:"short",day:"numeric",year:"numeric",timeZone:"UTC"}).format(new Date(value));
const relative=(value:string)=>{const seconds=Math.max(1,Math.floor((Date.now()-new Date(value).getTime())/1000));if(seconds<60)return `${seconds}s`;if(seconds<3600)return `${Math.floor(seconds/60)}m`;if(seconds<86400)return `${Math.floor(seconds/3600)}h`;return absolute(value)};
export function RelativeTime({value}:{value:string}){const[text,setText]=useState(()=>absolute(value));useEffect(()=>{const update=()=>setText(relative(value));update();const timer=setInterval(update,60_000);return()=>clearInterval(timer)},[value]);return <time dateTime={value} title={absolute(value)}>{text}</time>}
