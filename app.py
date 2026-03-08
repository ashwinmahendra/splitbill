from flask import Flask, request, jsonify
import os
import json
import re
import base64
import io

# Optional AI imports — app works without them
try:
    import google.generativeai as genai
    from PIL import Image
    HAS_AI = True
except ImportError:
    HAS_AI = False

app = Flask(__name__)

# ─────────────────────────────────────────────
#  FRONTEND (embedded React app)
# ─────────────────────────────────────────────
HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>SplitBill – Smart Bill Splitter</title>
  <script src="https://unpkg.com/react@18/umd/react.production.min.js"></script>
  <script src="https://unpkg.com/react-dom@18/umd/react-dom.production.min.js"></script>
  <script src="https://unpkg.com/@babel/standalone/babel.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/tesseract.js@5/dist/tesseract.min.js"></script>
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
           background: #e8f5ef; min-height: 100vh; display: flex; justify-content: center; }
    #root { width: 100%; max-width: 620px; }

    /* ── App shell ── */
    .app { min-height: 100vh; background: #fff; display: flex; flex-direction: column;
           box-shadow: 0 0 40px rgba(0,0,0,0.12); }

    /* ── Header ── */
    .header { background: linear-gradient(135deg, #1db87a 0%, #16a067 100%);
              color: #fff; padding: 20px 24px 0; flex-shrink: 0; }
    .header-top { display: flex; align-items: center; gap: 14px; margin-bottom: 18px; }
    .logo-wrap { width: 48px; height: 48px; border-radius: 14px; background: rgba(255,255,255,0.2);
                 display: flex; align-items: center; justify-content: center; font-size: 26px; }
    .app-title { font-size: 22px; font-weight: 800; letter-spacing: -0.5px; }
    .app-sub   { font-size: 12px; opacity: 0.8; margin-top: 2px; }

    /* ── Tabs ── */
    .tabs { display: flex; gap: 2px; }
    .tab  { flex: 1; padding: 10px 6px; border: none; background: rgba(255,255,255,0.12);
            color: rgba(255,255,255,0.75); font-size: 13px; font-weight: 600; cursor: pointer;
            border-radius: 8px 8px 0 0; transition: all .2s; display: flex; align-items: center;
            justify-content: center; gap: 5px; }
    .tab.active { background: #fff; color: #1db87a; }
    .tab:not(.active):hover { background: rgba(255,255,255,0.25); color: #fff; }
    .badge { min-width: 18px; height: 18px; padding: 0 5px; background: rgba(255,255,255,0.3);
             color: #fff; font-size: 11px; border-radius: 9px; display: flex; align-items: center;
             justify-content: center; line-height: 1; }
    .tab.active .badge { background: #1db87a; color: #fff; }

    /* ── Content ── */
    .content { padding: 24px; flex: 1; overflow-y: auto; }

    /* ── Cards ── */
    .card { border: 1.5px solid #eef1f4; border-radius: 14px; padding: 18px; margin-bottom: 14px; }
    .card-title { font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: .6px;
                  color: #aab; margin-bottom: 14px; }

    /* ── Avatar ── */
    .av { border-radius: 50%; display: flex; align-items: center; justify-content: center;
          color: #fff; font-weight: 800; flex-shrink: 0; }

    /* ── People list ── */
    .person-row { display: flex; align-items: center; gap: 12px; padding: 10px 0;
                  border-bottom: 1px solid #f3f4f6; }
    .person-row:last-child { border-bottom: none; }
    .person-name { flex: 1; font-size: 15px; font-weight: 500; }
    .btn-x { background: none; border: none; color: #ccc; cursor: pointer; font-size: 22px;
              line-height: 1; padding: 2px 6px; border-radius: 50%; transition: all .2s; }
    .btn-x:hover { background: #fff0f0; color: #e74c3c; }

    /* ── Inputs ── */
    .input-row { display: flex; gap: 8px; margin-top: 14px; }
    .input { flex: 1; padding: 11px 14px; border: 1.5px solid #e2e8f0; border-radius: 10px;
             font-size: 14px; outline: none; transition: border-color .2s; background: #fafbfc; }
    .input:focus { border-color: #1db87a; background: #fff; }
    .input-sm { width: 90px; flex: none; }
    .btn-green { padding: 11px 20px; background: #1db87a; color: #fff; border: none;
                 border-radius: 10px; font-size: 14px; font-weight: 700; cursor: pointer;
                 transition: all .2s; white-space: nowrap; }
    .btn-green:hover:not(:disabled) { background: #18a068; transform: translateY(-1px); }
    .btn-green:disabled { background: #a8dfc5; cursor: not-allowed; transform: none; }

    /* ── Upload zone ── */
    .upload-zone { border: 2.5px dashed #d1d5db; border-radius: 14px; padding: 44px 20px;
                   text-align: center; cursor: pointer; transition: all .25s; background: #fafbfc; }
    .upload-zone:hover, .upload-zone.drag  { border-color: #1db87a; background: #f0faf5; }
    .upload-icon  { font-size: 52px; margin-bottom: 12px; }
    .upload-text  { font-size: 15px; color: #64748b; font-weight: 500; }
    .upload-hint  { font-size: 12px; color: #9ca3af; margin-top: 4px; }
    .bill-preview { width: 100%; max-height: 280px; object-fit: contain; border-radius: 12px;
                    margin-bottom: 12px; border: 1px solid #e5e7eb; }
    .link-btn { background: none; border: none; color: #1db87a; font-size: 13px; cursor: pointer;
                text-decoration: underline; padding: 0; }

    /* ── Analyze btn ── */
    .btn-analyze { width: 100%; padding: 15px; background: linear-gradient(135deg, #1db87a, #16a067);
                   color: #fff; border: none; border-radius: 12px; font-size: 16px; font-weight: 700;
                   cursor: pointer; display: flex; align-items: center; justify-content: center;
                   gap: 10px; margin-top: 14px; transition: all .2s;
                   box-shadow: 0 4px 14px rgba(29,184,122,0.35); }
    .btn-analyze:hover:not(:disabled) { transform: translateY(-2px); box-shadow: 0 6px 20px rgba(29,184,122,0.4); }
    .btn-analyze:disabled { background: #a8dfc5; box-shadow: none; cursor: not-allowed; transform: none; }
    .spinner { width: 20px; height: 20px; border: 3px solid rgba(255,255,255,0.3);
               border-top-color: #fff; border-radius: 50%; animation: spin .7s linear infinite; }
    @keyframes spin { to { transform: rotate(360deg); } }

    /* ── Item cards (assign tab) ── */
    .item-box { border: 1.5px solid #eef1f4; border-radius: 12px; padding: 14px;
                margin-bottom: 10px; transition: border-color .2s; }
    .item-box:hover { border-color: #1db87a; }
    .item-hdr { display: flex; justify-content: space-between; align-items: flex-start;
                margin-bottom: 10px; gap: 8px; }
    .item-name  { font-size: 15px; font-weight: 600; }
    .item-price { font-size: 15px; font-weight: 800; color: #1db87a; white-space: nowrap; }
    .chips { display: flex; flex-wrap: wrap; gap: 6px; align-items: center; }
    .chip { display: flex; align-items: center; gap: 6px; padding: 5px 10px 5px 5px;
            border-radius: 20px; cursor: pointer; border: 2px solid #e5e7eb; transition: all .2s;
            font-size: 13px; font-weight: 600; color: #64748b; background: #f8fafc; user-select: none; }
    .chip.on { color: #fff; border-color: transparent; }
    .chip-av { width: 22px; height: 22px; border-radius: 50%; display: flex; align-items: center;
               justify-content: center; font-size: 9px; font-weight: 800; color: #fff; }

    /* ── Extras / tax-tip ── */
    .extra-row { display: flex; justify-content: space-between; align-items: center;
                 padding: 9px 0; border-top: 1px solid #f1f5f9; }
    .extra-lbl { font-size: 14px; color: #64748b; }
    .extra-amt { font-size: 14px; font-weight: 700; }
    .radio-grp { display: flex; gap: 8px; margin-top: 10px; }
    .radio-opt input { display: none; }
    .radio-opt { flex: 1; }
    .radio-lbl { display: block; text-align: center; padding: 9px 6px; border: 2px solid #e2e8f0;
                 border-radius: 9px; cursor: pointer; font-size: 13px; font-weight: 600;
                 color: #94a3b8; transition: all .2s; }
    .radio-opt input:checked + .radio-lbl { border-color: #1db87a; color: #1db87a; background: #f0fdf8; }

    /* ── Total bar ── */
    .total-bar { display: flex; justify-content: space-between; align-items: center;
                 padding: 16px 18px; background: #f0fdf8; border-radius: 12px; margin-top: 16px;
                 border: 1.5px solid #bbf7d0; }
    .total-lbl { font-size: 15px; font-weight: 600; color: #064e3b; }
    .total-amt { font-size: 24px; font-weight: 900; color: #1db87a; }

    /* ── Summary ── */
    .sum-row { display: flex; align-items: center; gap: 14px; padding: 15px;
               border: 1.5px solid #eef1f4; border-radius: 13px; margin-bottom: 10px; }
    .sum-info { flex: 1; }
    .sum-name   { font-size: 16px; font-weight: 700; }
    .sum-detail { font-size: 12px; color: #94a3b8; margin-top: 2px; line-height: 1.4; }
    .sum-amt    { font-size: 22px; font-weight: 900; color: #1db87a; }

    /* ── Settlement ── */
    .settle-row { display: flex; align-items: center; gap: 10px; padding: 12px 14px;
                  background: #f8fafc; border-radius: 10px; margin-bottom: 8px; font-size: 14px; }
    .arrow { color: #1db87a; font-size: 18px; flex-shrink: 0; }
    .settle-amt { margin-left: auto; font-weight: 800; color: #1db87a; font-size: 15px; }

    /* ── Alerts ── */
    .alert { padding: 12px 16px; border-radius: 10px; font-size: 14px; margin-bottom: 14px; }
    .alert-err  { background: #fef2f2; color: #b91c1c; border: 1px solid #fecaca; }
    .alert-info { background: #eff6ff; color: #1d4ed8; border: 1px solid #bfdbfe; }

    /* ── Empty state ── */
    .empty { text-align: center; padding: 50px 20px; color: #cbd5e1; }
    .empty-icon { font-size: 52px; margin-bottom: 14px; }
    .empty-txt  { font-size: 16px; font-weight: 500; }
    .empty-sub  { font-size: 13px; margin-top: 6px; }

    /* ── Next / secondary buttons ── */
    .btn-next { width: 100%; padding: 14px; background: #1db87a; color: #fff; border: none;
                border-radius: 12px; font-size: 15px; font-weight: 700; cursor: pointer;
                margin-top: 16px; transition: all .2s; }
    .btn-next:hover { background: #18a068; transform: translateY(-1px); }
    .btn-sec  { width: 100%; padding: 13px; background: #fff; color: #1db87a;
                border: 2px solid #1db87a; border-radius: 12px; font-size: 14px;
                font-weight: 700; cursor: pointer; margin-top: 10px; transition: all .2s; }
    .btn-sec:hover { background: #f0fdf8; }

    /* ── Select ── */
    .sel { width: 100%; padding: 11px 14px; border: 1.5px solid #e2e8f0; border-radius: 10px;
           font-size: 14px; background: #fafbfc; cursor: pointer; outline: none; }
    .sel:focus { border-color: #1db87a; }

    /* ── Restaurant name ── */
    .rest-name { font-size: 20px; font-weight: 800; margin-bottom: 4px; color: #111827; }
    .rest-sub  { font-size: 13px; color: #94a3b8; margin-bottom: 18px; }

    /* ── Mode toggle ── */
    .mode-toggle { display: flex; gap: 2px; background: #f1f5f9; border-radius: 10px;
                   padding: 3px; margin-bottom: 18px; }
    .mode-btn { flex: 1; padding: 10px 8px; border: none; border-radius: 8px; font-size: 13px;
                font-weight: 600; cursor: pointer; text-align: center; transition: all .2s;
                background: transparent; color: #94a3b8; }
    .mode-btn.active { background: #fff; color: #1db87a; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }

    /* ── Photo reference ── */
    .photo-ref { border: 1.5px solid #eef1f4; border-radius: 14px; margin-bottom: 16px;
                 overflow: hidden; }
    .photo-ref-header { display: flex; align-items: center; justify-content: space-between;
                        padding: 12px 16px; cursor: pointer; user-select: none; }
    .photo-ref-header:hover { background: #f8fafc; }
    .photo-ref-title { font-size: 13px; font-weight: 600; color: #64748b; }
    .photo-ref-arrow { font-size: 12px; color: #94a3b8; transition: transform .2s; }
    .photo-ref-arrow.open { transform: rotate(180deg); }
    .photo-ref-body { padding: 0 16px 14px; }
    .photo-ref-img { width: 100%; max-height: 300px; object-fit: contain; border-radius: 10px;
                     border: 1px solid #e5e7eb; }
    .photo-ref-upload { border: 2px dashed #d1d5db; border-radius: 10px; padding: 24px 16px;
                        text-align: center; cursor: pointer; transition: all .2s; background: #fafbfc; }
    .photo-ref-upload:hover { border-color: #1db87a; background: #f0faf5; }

    /* ── Manual item row ── */
    .manual-item { display: flex; align-items: center; gap: 10px; padding: 10px 0;
                   border-bottom: 1px solid #f3f4f6; cursor: pointer; }
    .manual-item:last-child { border-bottom: none; }
    .manual-item:hover { background: #f8fafc; margin: 0 -8px; padding: 10px 8px; border-radius: 8px; }
    .manual-item-name { flex: 1; font-size: 14px; font-weight: 500; }
    .manual-item-price { font-size: 14px; font-weight: 700; color: #1db87a; }
    .edit-hint { font-size: 11px; color: #94a3b8; margin-left: auto; }

    /* ── Inline edit row ── */
    .edit-row { display: flex; gap: 6px; padding: 8px 0; border-bottom: 1px solid #f3f4f6;
                align-items: center; }
    .edit-row:last-child { border-bottom: none; }
    .edit-input { padding: 8px 10px; border: 1.5px solid #1db87a; border-radius: 8px;
                  font-size: 13px; outline: none; background: #fff; }
    .edit-input-name { flex: 1; }
    .edit-input-price { width: 80px; }
    .btn-save { padding: 7px 12px; background: #1db87a; color: #fff; border: none;
                border-radius: 8px; font-size: 12px; font-weight: 700; cursor: pointer; }
    .btn-cancel { padding: 7px 10px; background: none; color: #94a3b8; border: 1.5px solid #e2e8f0;
                  border-radius: 8px; font-size: 12px; font-weight: 600; cursor: pointer; }

    /* ── Math warning ── */
    .alert-warn { background: #fffbeb; color: #92400e; border: 1px solid #fde68a; }

    /* ── OCR progress ── */
    .ocr-bar { margin-top: 10px; }
    .ocr-progress { height: 6px; background: #e2e8f0; border-radius: 3px; overflow: hidden; }
    .ocr-fill { height: 100%; background: linear-gradient(90deg, #1db87a, #16a067);
                border-radius: 3px; transition: width .3s; }
    .ocr-status { font-size: 12px; color: #64748b; margin-top: 6px; text-align: center; }
    .btn-ocr { width: 100%; padding: 12px; background: linear-gradient(135deg, #6366f1, #4f46e5);
               color: #fff; border: none; border-radius: 10px; font-size: 14px; font-weight: 700;
               cursor: pointer; display: flex; align-items: center; justify-content: center;
               gap: 8px; margin-top: 10px; transition: all .2s;
               box-shadow: 0 3px 10px rgba(99,102,241,0.3); }
    .btn-ocr:hover:not(:disabled) { transform: translateY(-1px); box-shadow: 0 5px 15px rgba(99,102,241,0.4); }
    .btn-ocr:disabled { opacity: 0.6; cursor: not-allowed; transform: none; }
    .ocr-note { font-size: 11px; color: #94a3b8; text-align: center; margin-top: 6px; }

    /* ── Tax/tip inputs ── */
    .field-row { display: flex; align-items: center; gap: 10px; margin-top: 12px; }
    .field-label { font-size: 14px; color: #64748b; font-weight: 500; width: 50px; }
    .field-input { flex: 1; padding: 10px 14px; border: 1.5px solid #e2e8f0; border-radius: 10px;
                   font-size: 14px; outline: none; background: #fafbfc; }
    .field-input:focus { border-color: #1db87a; background: #fff; }

    @media (max-width: 480px) {
      .tab { font-size: 11px; padding: 9px 4px; }
      .content { padding: 16px; }
      .total-amt { font-size: 20px; }
    }
  </style>
</head>
<body>
<div id="root"></div>
<script type="text/babel">
const { useState, useRef, useEffect } = React;

const PALETTE = [
  '#FF6B6B','#4ECDC4','#45B7D1','#A29BFE',
  '#FD79A8','#FDCB6E','#6C5CE7','#00B894',
  '#E17055','#74B9FF'
];

const ini = name =>
  name.trim().split(/\s+/).map(w => w[0]).join('').toUpperCase().slice(0, 2) || '?';

const fmt = (n, cur = '$') =>
  `${cur}${(+(n) || 0).toFixed(2)}`;

// ── Avatar
function Av({ name, color, size = 40 }) {
  return (
    <div className="av"
      style={{ width: size, height: size, background: color, fontSize: size * 0.33 }}>
      {ini(name)}
    </div>
  );
}

// ── Main App
function App() {
  // State
  const [tab, setTab]             = useState('people');
  const [people, setPeople]       = useState([]);
  const [newName, setNewName]     = useState('');
  const [imgPrev, setImgPrev]     = useState(null);
  const [imgData, setImgData]     = useState(null);
  const [imgType, setImgType]     = useState('image/jpeg');
  const [bill, setBill]           = useState(null);
  const [assignments, setAsgn]    = useState({});
  const [taxSplit, setTaxSplit]   = useState('equal');
  const [payerId, setPayerId]     = useState('');
  const [analyzing, setAnalyzing] = useState(false);
  const [error, setError]         = useState(null);
  const [drag, setDrag]           = useState(false);
  const fileRef = useRef(null);

  // Manual entry state
  const [billMode, setBillMode]       = useState('manual'); // 'manual' or 'scan'
  const [manualItems, setManualItems] = useState([]);
  const [newItemName, setNewItemName] = useState('');
  const [newItemPrice, setNewItemPrice] = useState('');
  const [manualTax, setManualTax]     = useState('');
  const [manualTip, setManualTip]     = useState('');
  const [hasAI, setHasAI]             = useState(false);
  const [manualTotal, setManualTotal] = useState('');
  const [editingIdx, setEditingIdx]   = useState(null);
  const [editName, setEditName]       = useState('');
  const [editPrice, setEditPrice]     = useState('');
  const [refPhoto, setRefPhoto]       = useState(null);
  const [refPhotoOpen, setRefPhotoOpen] = useState(true);
  const refPhotoRef = useRef(null);
  const [ocrScanning, setOcrScanning] = useState(false);
  const [ocrProgress, setOcrProgress] = useState(0);
  const [ocrStatus, setOcrStatus]     = useState('');

  // Check if AI is available
  useEffect(() => {
    fetch('/api/check-ai').then(r => r.json()).then(d => {
      setHasAI(d.available);
      if (!d.available) setBillMode('manual');
    }).catch(() => {});
  }, []);

  // ── People helpers
  const addPerson = e => {
    e?.preventDefault();
    const n = newName.trim();
    if (!n) return;
    setPeople(p => [...p, {
      id: `p${Date.now()}`,
      name: n,
      color: PALETTE[p.length % PALETTE.length]
    }]);
    setNewName('');
  };

  const removePerson = id => {
    setPeople(p => p.filter(x => x.id !== id));
    setAsgn(a => {
      const next = { ...a };
      Object.keys(next).forEach(k => {
        next[k] = next[k].filter(pid => pid !== id);
      });
      return next;
    });
  };

  // ── Image helpers
  const loadFile = file => {
    if (!file || !file.type.startsWith('image/')) return;
    setImgType(file.type);
    const r = new FileReader();
    r.onload = e => {
      setImgPrev(e.target.result);
      setImgData(e.target.result);
      setBill(null);
      setAsgn({});
      setError(null);
    };
    r.readAsDataURL(file);
  };

  const resetImage = () => {
    setImgPrev(null); setImgData(null); setBill(null); setError(null);
  };

  // ── Analyze (AI scan)
  const analyze = async () => {
    if (!imgData || people.length < 2) return;
    setAnalyzing(true); setError(null);
    try {
      const res = await fetch('/api/analyze-bill', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ image: imgData, mediaType: imgType })
      });
      const data = await res.json();
      if (data.error) throw new Error(data.error);
      setBill(data);
      const init = {};
      (data.items || []).forEach((_, i) => {
        init[i] = people.map(p => p.id);
      });
      setAsgn(init);
      setTab('assign');
    } catch (err) {
      setError(err.message);
    } finally {
      setAnalyzing(false);
    }
  };

  // ── Manual entry helpers
  const addManualItem = e => {
    e?.preventDefault();
    const name = newItemName.trim();
    const price = parseFloat(newItemPrice);
    if (!name || isNaN(price) || price <= 0) return;
    setManualItems(items => [...items, { name, price, quantity: 1 }]);
    setNewItemName('');
    setNewItemPrice('');
  };

  const removeManualItem = idx => {
    setManualItems(items => items.filter((_, i) => i !== idx));
    if (editingIdx === idx) setEditingIdx(null);
  };

  const startEdit = idx => {
    setEditingIdx(idx);
    setEditName(manualItems[idx].name);
    setEditPrice(String(manualItems[idx].price));
  };

  const saveEdit = () => {
    const name = editName.trim();
    const price = parseFloat(editPrice);
    if (!name || isNaN(price) || price <= 0) return;
    setManualItems(items => items.map((it, i) =>
      i === editingIdx ? { ...it, name, price } : it
    ));
    setEditingIdx(null);
  };

  const cancelEdit = () => setEditingIdx(null);

  // ── OCR scanning
  const runOCR = async () => {
    if (!refPhoto || ocrScanning) return;
    setOcrScanning(true);
    setOcrProgress(0);
    setOcrStatus('Loading OCR engine…');
    try {
      const result = await Tesseract.recognize(refPhoto, 'eng', {
        logger: m => {
          if (m.status === 'recognizing text') {
            setOcrProgress(Math.round(m.progress * 100));
            setOcrStatus('Reading bill…');
          } else if (m.status === 'loading language traineddata') {
            setOcrStatus('Loading language data…');
          }
        }
      });

      const text = result.data.text;
      const lines = text.split('\n').map(l => l.trim()).filter(Boolean);

      // Parse lines for items with prices
      const items = [];
      let foundTax = null;
      let foundTip = null;
      let foundTotal = null;

      // Keywords to skip (not individual items)
      const skipWords = /^(subtotal|sub total|total|amount due|balance|change|cash|card|visa|mastercard|amex|thank|welcome|order|table|server|guest|date|time|receipt|invoice|check|tel|phone|fax|www|http|address|\d{1,2}[\/\-]\d{1,2})/i;
      const taxWords = /^(tax|vat|gst|hst|sales tax|state tax)/i;
      const tipWords = /^(tip|gratuity|service charge|service fee|svc)/i;
      const totalWords = /^(total|amount due|balance due|grand total)/i;

      for (const line of lines) {
        // Find price pattern: digits with decimal (e.g., 12.50, $12.50)
        const priceMatch = line.match(/\$?\s*(\d+\.\d{2})\s*$/);
        if (!priceMatch) continue;

        const price = parseFloat(priceMatch[1]);
        if (isNaN(price) || price <= 0) continue;

        // Get the name part (everything before the price)
        let name = line.slice(0, line.lastIndexOf(priceMatch[0])).trim();
        // Clean up leading special chars, quantities like "1x", "2 x"
        name = name.replace(/^[\d]+\s*[xX×]\s*/, '').replace(/^[^a-zA-Z]+/, '').trim();

        if (!name || name.length < 2) continue;

        // Categorize
        if (taxWords.test(name)) {
          foundTax = price;
        } else if (tipWords.test(name)) {
          foundTip = price;
        } else if (totalWords.test(name)) {
          foundTotal = price;
        } else if (!skipWords.test(name)) {
          items.push({ name, price, quantity: 1 });
        }
      }

      if (items.length === 0) {
        setOcrStatus('No items found. Try a clearer photo or enter manually.');
        setOcrScanning(false);
        return;
      }

      // Populate the form
      setManualItems(prev => [...prev, ...items]);
      if (foundTax != null && !manualTax) setManualTax(String(foundTax));
      if (foundTip != null && !manualTip) setManualTip(String(foundTip));
      if (foundTotal != null && !manualTotal) setManualTotal(String(foundTotal));
      setRefPhotoOpen(false);
      setOcrStatus(`Found ${items.length} item${items.length > 1 ? 's' : ''}! Review and edit below.`);
    } catch (err) {
      setOcrStatus('OCR failed: ' + err.message);
    } finally {
      setOcrScanning(false);
    }
  };

  const finishManualEntry = () => {
    if (manualItems.length === 0 || people.length < 2) return;
    const tax = parseFloat(manualTax) || 0;
    const tip = parseFloat(manualTip) || 0;
    const subtotal = manualItems.reduce((s, it) => s + it.price, 0);
    const billData = {
      restaurant: '',
      items: manualItems,
      subtotal,
      tax,
      tip,
      total: subtotal + tax + tip,
      currency: '$'
    };
    setBill(billData);
    const init = {};
    manualItems.forEach((_, i) => {
      init[i] = people.map(p => p.id);
    });
    setAsgn(init);
    setTab('assign');
  };

  // ── Assignment toggle
  const toggle = (idx, pid) => {
    setAsgn(a => {
      const cur = a[idx] || [];
      return {
        ...a,
        [idx]: cur.includes(pid) ? cur.filter(x => x !== pid) : [...cur, pid]
      };
    });
  };

  // ── Split calculation
  const calcSplits = () => {
    if (!bill || !people.length) return {};
    const totals = {};
    people.forEach(p => { totals[p.id] = 0; });

    (bill.items || []).forEach((item, i) => {
      const who = assignments[i] || [];
      if (!who.length) return;
      const share = item.price / who.length;
      who.forEach(pid => { totals[pid] = (totals[pid] || 0) + share; });
    });

    const extras = (bill.tax || 0) + (bill.tip || 0);
    if (extras > 0) {
      if (taxSplit === 'equal') {
        const sh = extras / people.length;
        people.forEach(p => { totals[p.id] += sh; });
      } else {
        const itemSum = Object.values(totals).reduce((s, v) => s + v, 0);
        if (itemSum > 0) {
          people.forEach(p => {
            totals[p.id] += extras * (totals[p.id] / itemSum);
          });
        } else {
          const sh = extras / people.length;
          people.forEach(p => { totals[p.id] += sh; });
        }
      }
    }
    return totals;
  };

  const splits     = calcSplits();
  const cur        = (bill && bill.currency) || '$';
  const grandTotal = bill
    ? (bill.total || (bill.subtotal || 0) + (bill.tax || 0) + (bill.tip || 0))
    : 0;

  // Settlement
  const settlement = (() => {
    if (!payerId || !bill) return [];
    const payer = people.find(p => p.id === payerId);
    if (!payer) return [];
    return people
      .filter(p => p.id !== payerId)
      .map(p => ({ from: p, to: payer, amount: splits[p.id] || 0 }))
      .filter(s => s.amount > 0.005);
  })();

  // ── Tabs definition
  const TABS = [
    { id: 'people',  label: 'People',  badge: people.length || null },
    { id: 'bill',    label: 'Bill',    badge: null },
    { id: 'assign',  label: 'Assign',  badge: bill ? (bill.items || []).length : null },
    { id: 'summary', label: 'Summary', badge: null },
  ];

  // ════════════════════════════════════════
  // RENDER: People tab
  // ════════════════════════════════════════
  const TabPeople = () => (
    <div className="content">
      <div className="card-title">Add everyone splitting the bill</div>

      {people.length === 0 ? (
        <div className="empty">
          <div className="empty-icon">👥</div>
          <div className="empty-txt">No people yet</div>
          <div className="empty-sub">Add at least 2 people to start splitting</div>
        </div>
      ) : (
        <div className="card">
          {people.map(p => (
            <div key={p.id} className="person-row">
              <Av name={p.name} color={p.color} />
              <span className="person-name">{p.name}</span>
              <button className="btn-x" onClick={() => removePerson(p.id)} title="Remove">×</button>
            </div>
          ))}
        </div>
      )}

      <form className="input-row" onSubmit={addPerson}>
        <input
          className="input"
          placeholder="Enter a name…"
          value={newName}
          onChange={e => setNewName(e.target.value)}
          autoFocus
        />
        <button className="btn-green" type="submit" disabled={!newName.trim()}>
          Add
        </button>
      </form>

      {people.length >= 2 && (
        <button className="btn-next" onClick={() => setTab('bill')}>
          Continue to Bill →
        </button>
      )}
    </div>
  );

  // ════════════════════════════════════════
  // RENDER: Bill tab
  // ════════════════════════════════════════
  const TabBill = () => {
    const manualSubtotal = manualItems.reduce((s, it) => s + it.price, 0);

    return (
      <div className="content">
        {people.length < 2 && (
          <div className="alert alert-info">
            Please add at least 2 people in the <strong>People</strong> tab first.
          </div>
        )}

        {/* Mode toggle */}
        <div className="mode-toggle">
          <button
            className={`mode-btn ${billMode === 'manual' ? 'active' : ''}`}
            onClick={() => setBillMode('manual')}
          >
            ✏️ Enter Manually
          </button>
          {hasAI && (
            <button
              className={`mode-btn ${billMode === 'scan' ? 'active' : ''}`}
              onClick={() => setBillMode('scan')}
            >
              📸 Scan with AI
            </button>
          )}
        </div>

        {/* ── MANUAL MODE ── */}
        {billMode === 'manual' && (
          <>
            {/* Photo reference */}
            <div className="photo-ref">
              <div className="photo-ref-header" onClick={() => refPhoto && setRefPhotoOpen(o => !o)}>
                <span className="photo-ref-title">
                  {refPhoto ? '📷 Bill Photo Reference' : '📷 Upload bill photo (optional)'}
                </span>
                {refPhoto && (
                  <span className={`photo-ref-arrow ${refPhotoOpen ? 'open' : ''}`}>▼</span>
                )}
              </div>
              {(!refPhoto || refPhotoOpen) && (
                <div className="photo-ref-body">
                  {!refPhoto ? (
                    <div className="photo-ref-upload" onClick={() => refPhotoRef.current?.click()}>
                      <div style={{ fontSize: 28, marginBottom: 6 }}>📸</div>
                      <div style={{ fontSize: 13, color: '#64748b', fontWeight: 500 }}>
                        Tap to upload a bill photo for reference
                      </div>
                      <div style={{ fontSize: 11, color: '#9ca3af', marginTop: 3 }}>
                        JPG · PNG · HEIC · WEBP
                      </div>
                    </div>
                  ) : (
                    <>
                      <img src={refPhoto} className="photo-ref-img" alt="Bill reference" />

                      <button
                        className="btn-ocr"
                        onClick={runOCR}
                        disabled={ocrScanning}
                      >
                        {ocrScanning
                          ? <><div className="spinner"></div> Scanning…</>
                          : <><span>🔍</span> Extract Items from Photo</>
                        }
                      </button>
                      <div className="ocr-note">
                        Free OCR — runs in your browser, no data sent to servers
                      </div>

                      {ocrScanning && (
                        <div className="ocr-bar">
                          <div className="ocr-progress">
                            <div className="ocr-fill" style={{ width: `${ocrProgress}%` }}></div>
                          </div>
                        </div>
                      )}

                      {ocrStatus && (
                        <div className="ocr-status">{ocrStatus}</div>
                      )}

                      <div style={{ marginTop: 8, textAlign: 'center' }}>
                        <button className="link-btn" onClick={() => { setRefPhoto(null); setOcrStatus(''); }}>
                          ✕ Remove photo
                        </button>
                      </div>
                    </>
                  )}
                </div>
              )}
              <input
                ref={refPhotoRef}
                type="file"
                accept="image/*"
                style={{ display: 'none' }}
                onChange={e => {
                  const file = e.target.files[0];
                  if (!file || !file.type.startsWith('image/')) return;
                  const r = new FileReader();
                  r.onload = ev => setRefPhoto(ev.target.result);
                  r.readAsDataURL(file);
                  e.target.value = '';
                }}
              />
            </div>

            <div className="card-title">Add bill items</div>

            {manualItems.length > 0 && (
              <div className="card">
                {manualItems.map((item, i) => (
                  editingIdx === i ? (
                    <div key={i} className="edit-row">
                      <input
                        className="edit-input edit-input-name"
                        value={editName}
                        onChange={e => setEditName(e.target.value)}
                        autoFocus
                        onKeyDown={e => { if (e.key === 'Enter') saveEdit(); if (e.key === 'Escape') cancelEdit(); }}
                      />
                      <input
                        className="edit-input edit-input-price"
                        type="number"
                        step="0.01"
                        min="0"
                        value={editPrice}
                        onChange={e => setEditPrice(e.target.value)}
                        onKeyDown={e => { if (e.key === 'Enter') saveEdit(); if (e.key === 'Escape') cancelEdit(); }}
                      />
                      <button className="btn-save" onClick={saveEdit}>Save</button>
                      <button className="btn-cancel" onClick={cancelEdit}>✕</button>
                    </div>
                  ) : (
                    <div key={i} className="manual-item" onClick={() => startEdit(i)}>
                      <span className="manual-item-name">{item.name}</span>
                      <span className="manual-item-price">{fmt(item.price)}</span>
                      <button className="btn-x" onClick={e => { e.stopPropagation(); removeManualItem(i); }} title="Remove">×</button>
                    </div>
                  )
                ))}
              </div>
            )}

            <form className="input-row" onSubmit={addManualItem}>
              <input
                className="input"
                placeholder="Item name…"
                value={newItemName}
                onChange={e => setNewItemName(e.target.value)}
              />
              <input
                className="input input-sm"
                placeholder="Price"
                type="number"
                step="0.01"
                min="0"
                value={newItemPrice}
                onChange={e => setNewItemPrice(e.target.value)}
              />
              <button
                className="btn-green"
                type="submit"
                disabled={!newItemName.trim() || !newItemPrice || parseFloat(newItemPrice) <= 0}
              >
                Add
              </button>
            </form>

            {manualItems.length > 0 && (
              <>
                <div className="card" style={{ marginTop: 18 }}>
                  <div className="card-title">Tax & Tip (optional)</div>
                  <div className="field-row">
                    <span className="field-label">Tax</span>
                    <input
                      className="field-input"
                      type="number"
                      step="0.01"
                      min="0"
                      placeholder="0.00"
                      value={manualTax}
                      onChange={e => setManualTax(e.target.value)}
                    />
                  </div>
                  <div className="field-row">
                    <span className="field-label">Tip</span>
                    <input
                      className="field-input"
                      type="number"
                      step="0.01"
                      min="0"
                      placeholder="0.00"
                      value={manualTip}
                      onChange={e => setManualTip(e.target.value)}
                    />
                  </div>
                </div>

                <div className="card" style={{ marginTop: 12 }}>
                  <div className="card-title">Bill Total (from receipt)</div>
                  <div className="field-row" style={{ marginTop: 0 }}>
                    <span className="field-label">Total</span>
                    <input
                      className="field-input"
                      type="number"
                      step="0.01"
                      min="0"
                      placeholder="Enter total from receipt…"
                      value={manualTotal}
                      onChange={e => setManualTotal(e.target.value)}
                    />
                  </div>
                </div>

                {(() => {
                  const calcTotal = manualSubtotal + (parseFloat(manualTax) || 0) + (parseFloat(manualTip) || 0);
                  const expected = parseFloat(manualTotal);
                  const hasExpected = manualTotal !== '' && !isNaN(expected) && expected > 0;
                  const diff = hasExpected ? Math.abs(calcTotal - expected) : 0;
                  const mathOk = !hasExpected || diff < 0.02;
                  return (
                    <>
                      <div className="total-bar" style={!mathOk ? { borderColor: '#fde68a', background: '#fffbeb' } : {}}>
                        <div>
                          <span className="total-lbl">Calculated Total</span>
                          {hasExpected && mathOk && (
                            <div style={{ fontSize: 11, color: '#16a34a', fontWeight: 600, marginTop: 2 }}>
                              Math checks out!
                            </div>
                          )}
                        </div>
                        <span className="total-amt" style={!mathOk ? { color: '#dc2626' } : {}}>
                          {fmt(calcTotal)}
                        </span>
                      </div>

                      {!mathOk && (
                        <div className="alert alert-warn" style={{ marginTop: 10 }}>
                          Math doesn't add up! Your items + tax + tip = <strong>{fmt(calcTotal)}</strong> but the receipt says <strong>{fmt(expected)}</strong>.
                          {' '}Off by <strong>{fmt(diff)}</strong>. Tap an item to edit it, or check tax/tip.
                        </div>
                      )}
                    </>
                  );
                })()}

                <button
                  className="btn-next"
                  onClick={finishManualEntry}
                  disabled={people.length < 2}
                >
                  Continue to Assign →
                </button>
              </>
            )}
          </>
        )}

        {/* ── SCAN MODE ── */}
        {billMode === 'scan' && (
          <>
            <div className="card-title">Upload your bill photo</div>

            {!imgPrev ? (
              <div
                className={`upload-zone ${drag ? 'drag' : ''}`}
                onClick={() => fileRef.current?.click()}
                onDragOver={e => { e.preventDefault(); setDrag(true); }}
                onDragLeave={() => setDrag(false)}
                onDrop={e => { e.preventDefault(); setDrag(false); loadFile(e.dataTransfer.files[0]); }}
              >
                <div className="upload-icon">📸</div>
                <div className="upload-text">Tap or drag & drop a photo</div>
                <div className="upload-hint">JPG · PNG · HEIC · WEBP</div>
              </div>
            ) : (
              <>
                <img src={imgPrev} className="bill-preview" alt="Bill preview" />
                <div style={{ marginBottom: 14 }}>
                  <button className="link-btn" onClick={resetImage}>✕ Remove & use a different photo</button>
                </div>
              </>
            )}

            <input
              ref={fileRef}
              type="file"
              accept="image/*"
              style={{ display: 'none' }}
              onChange={e => loadFile(e.target.files[0])}
            />

            {error && (
              <div className="alert alert-err" style={{ marginTop: 14 }}>
                ⚠️ {error}
              </div>
            )}

            {imgPrev && (
              <button
                className="btn-analyze"
                onClick={analyze}
                disabled={analyzing || people.length < 2}
              >
                {analyzing
                  ? <><div className="spinner"></div> AI is reading your bill…</>
                  : <><span>✨</span> Analyze Bill with AI</>
                }
              </button>
            )}
          </>
        )}
      </div>
    );
  };

  // ════════════════════════════════════════
  // RENDER: Assign tab
  // ════════════════════════════════════════
  const TabAssign = () => {
    if (!bill) return (
      <div className="content">
        <div className="empty">
          <div className="empty-icon">🧾</div>
          <div className="empty-txt">No bill entered yet</div>
          <div className="empty-sub">Go to the Bill tab to add items</div>
        </div>
      </div>
    );

    return (
      <div className="content">
        {bill.restaurant && <div className="rest-name">{bill.restaurant}</div>}
        <div className="rest-sub">Tap people's names to assign each item</div>

        {(bill.items || []).map((item, i) => {
          const who = assignments[i] || [];
          const allOn = who.length === people.length;
          return (
            <div key={i} className="item-box">
              <div className="item-hdr">
                <span className="item-name">
                  {item.name}
                  {item.quantity > 1 ? ` ×${item.quantity}` : ''}
                </span>
                <span className="item-price">{fmt(item.price, cur)}</span>
              </div>
              <div className="chips">
                {people.map(p => {
                  const on = who.includes(p.id);
                  return (
                    <div
                      key={p.id}
                      className={`chip ${on ? 'on' : ''}`}
                      style={on ? { background: p.color } : {}}
                      onClick={() => toggle(i, p.id)}
                    >
                      <div
                        className="chip-av"
                        style={{ background: on ? 'rgba(255,255,255,0.28)' : p.color }}
                      >
                        {ini(p.name)}
                      </div>
                      {p.name.split(' ')[0]}
                    </div>
                  );
                })}
                <button
                  className="link-btn"
                  style={{ fontSize: 12 }}
                  onClick={() =>
                    setAsgn(a => ({
                      ...a,
                      [i]: allOn ? [] : people.map(p => p.id)
                    }))
                  }
                >
                  {allOn ? 'clear' : 'all'}
                </button>
              </div>
            </div>
          );
        })}

        {/* Tax & tip section */}
        {((bill.tax || 0) > 0 || (bill.tip || 0) > 0) && (
          <div className="card" style={{ marginTop: 6 }}>
            <div className="card-title">Tax & Tip</div>
            {(bill.tax || 0) > 0 && (
              <div className="extra-row">
                <span className="extra-lbl">Tax</span>
                <span className="extra-amt">{fmt(bill.tax, cur)}</span>
              </div>
            )}
            {(bill.tip || 0) > 0 && (
              <div className="extra-row">
                <span className="extra-lbl">Tip / Service charge</span>
                <span className="extra-amt">{fmt(bill.tip, cur)}</span>
              </div>
            )}
            <div className="card-title" style={{ marginTop: 14, marginBottom: 8 }}>
              How to split tax & tip?
            </div>
            <div className="radio-grp">
              {[['equal', 'Split equally'], ['proportional', 'By item totals']].map(([v, label]) => (
                <label key={v} className="radio-opt">
                  <input type="radio" checked={taxSplit === v} onChange={() => setTaxSplit(v)} />
                  <span className="radio-lbl">{label}</span>
                </label>
              ))}
            </div>
          </div>
        )}

        <div className="total-bar">
          <span className="total-lbl">Bill Total</span>
          <span className="total-amt">{fmt(grandTotal, cur)}</span>
        </div>

        <button className="btn-next" onClick={() => setTab('summary')}>
          View Split Summary →
        </button>
      </div>
    );
  };

  // ════════════════════════════════════════
  // RENDER: Summary tab
  // ════════════════════════════════════════
  const TabSummary = () => {
    if (!bill || !people.length) return (
      <div className="content">
        <div className="empty">
          <div className="empty-icon">📊</div>
          <div className="empty-txt">Nothing to show yet</div>
          <div className="empty-sub">Complete the previous steps first</div>
        </div>
      </div>
    );

    return (
      <div className="content">
        <div className="card-title">Each person owes</div>

        {people.map(p => {
          const myItems = (bill.items || [])
            .filter((_, i) => (assignments[i] || []).includes(p.id))
            .map(it => it.name);

          return (
            <div key={p.id} className="sum-row">
              <Av name={p.name} color={p.color} size={48} />
              <div className="sum-info">
                <div className="sum-name">{p.name}</div>
                <div className="sum-detail">
                  {myItems.length ? myItems.join(', ') : 'No items assigned'}
                </div>
              </div>
              <div className="sum-amt">{fmt(splits[p.id] || 0, cur)}</div>
            </div>
          );
        })}

        {/* Who paid */}
        <div style={{ marginTop: 24 }}>
          <div className="card-title">Who paid the bill?</div>
          <select
            className="sel"
            value={payerId}
            onChange={e => setPayerId(e.target.value)}
          >
            <option value="">— Select (optional) —</option>
            {people.map(p => (
              <option key={p.id} value={p.id}>{p.name}</option>
            ))}
          </select>
        </div>

        {/* Settlement */}
        {settlement.length > 0 && (
          <div style={{ marginTop: 20 }}>
            <div className="card-title">Settlement</div>
            {settlement.map((s, i) => (
              <div key={i} className="settle-row">
                <Av name={s.from.name} color={s.from.color} size={32} />
                <strong>{s.from.name}</strong>
                <span className="arrow">→</span>
                <Av name={s.to.name} color={s.to.color} size={32} />
                <strong>{s.to.name}</strong>
                <span className="settle-amt">{fmt(s.amount, cur)}</span>
              </div>
            ))}
          </div>
        )}

        <div className="total-bar" style={{ marginTop: 20 }}>
          <span className="total-lbl">Grand Total</span>
          <span className="total-amt">{fmt(grandTotal, cur)}</span>
        </div>

        {/* Copy summary */}
        <button
          className="btn-sec"
          onClick={() => {
            const lines = people
              .map(p => `${p.name}: ${fmt(splits[p.id] || 0, cur)}`)
              .join('\n');
            const slines = settlement
              .map(s => `${s.from.name} pays ${s.to.name} ${fmt(s.amount, cur)}`)
              .join('\n');
            const txt =
              `SplitBill${bill.restaurant ? ' — ' + bill.restaurant : ''}\n\n` +
              lines +
              (slines ? '\n\nSettlement:\n' + slines : '');
            if (navigator.clipboard) {
              navigator.clipboard.writeText(txt).then(() => alert('Copied to clipboard!'));
            } else {
              alert(txt);
            }
          }}
        >
          Copy Summary
        </button>

        {/* Start over */}
        <button
          className="btn-sec"
          style={{ marginTop: 8, borderColor: '#e2e8f0', color: '#94a3b8' }}
          onClick={() => {
            setBill(null); setImgPrev(null); setImgData(null);
            setAsgn({}); setPayerId(''); setError(null);
            setManualItems([]); setManualTax(''); setManualTip('');
            setManualTotal(''); setRefPhoto(null); setTab('bill');
          }}
        >
          Split Another Bill
        </button>
      </div>
    );
  };

  // ════════════════════════════════════════
  // ROOT RENDER
  // ════════════════════════════════════════
  return (
    <div className="app">
      {/* Header */}
      <div className="header">
        <div className="header-top">
          <div className="logo-wrap">💸</div>
          <div>
            <div className="app-title">SplitBill</div>
            <div className="app-sub">Smart bill splitting with friends</div>
          </div>
        </div>
        <div className="tabs">
          {TABS.map(t => (
            <button
              key={t.id}
              className={`tab ${tab === t.id ? 'active' : ''}`}
              onClick={() => setTab(t.id)}
            >
              {t.label}
              {t.badge !== null && t.badge !== undefined && (
                <span className="badge">{t.badge}</span>
              )}
            </button>
          ))}
        </div>
      </div>

      {/* Tab content */}
      {tab === 'people'  && <TabPeople  />}
      {tab === 'bill'    && <TabBill    />}
      {tab === 'assign'  && <TabAssign  />}
      {tab === 'summary' && <TabSummary />}
    </div>
  );
}

ReactDOM.createRoot(document.getElementById('root')).render(<App />);
</script>
</body>
</html>"""


# ─────────────────────────────────────────────
#  ROUTES
# ─────────────────────────────────────────────

@app.route('/')
def index():
    return HTML


@app.route('/api/check-ai')
def check_ai():
    available = HAS_AI and bool(os.environ.get('GEMINI_API_KEY', '').strip())
    return jsonify({'available': available})


@app.route('/api/analyze-bill', methods=['POST'])
def analyze_bill():
    if not HAS_AI:
        return jsonify({'error': 'AI scanning is not available. Use manual entry instead.'}), 400

    try:
        body       = request.get_json(force=True)
        image_data = body.get('image', '')

        # Strip data-URL prefix to get raw base64
        if ',' in image_data:
            image_data = image_data.split(',', 1)[1]

        api_key = os.environ.get('GEMINI_API_KEY', '').strip()
        if not api_key:
            return jsonify({'error': 'GEMINI_API_KEY is not set. Use manual entry instead.'}), 500

        # Decode image and load with PIL
        image_bytes = base64.b64decode(image_data)
        image = Image.open(io.BytesIO(image_bytes))

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.0-flash')

        prompt = (
            'Analyze this bill or receipt image carefully. '
            'Return ONLY a valid JSON object — no markdown, no explanation:\n\n'
            '{\n'
            '  "restaurant": "Name of restaurant or store, or empty string",\n'
            '  "items": [\n'
            '    {"name": "Item description", "price": 12.50, "quantity": 1}\n'
            '  ],\n'
            '  "subtotal": 45.00,\n'
            '  "tax": 3.60,\n'
            '  "tip": 0.00,\n'
            '  "total": 48.60,\n'
            '  "currency": "$"\n'
            '}\n\n'
            'Rules:\n'
            '- List EVERY line-item on the bill with its individual price.\n'
            '- If quantity > 1 and a unit price is visible, list one entry with quantity field set.\n'
            '- subtotal = sum of items before tax.\n'
            '- tax = any tax / VAT / GST amount shown (0 if absent).\n'
            '- tip = any tip, gratuity, or service charge (0 if absent).\n'
            '- total = the final charged amount. If not shown, compute subtotal+tax+tip.\n'
            '- currency = the symbol used on the bill (default "$").\n'
            'Return ONLY the JSON object, nothing else.'
        )

        response = model.generate_content([prompt, image])
        text = response.text.strip()

        # Strip markdown code fences if model added them
        text = re.sub(r'^```(?:json)?\s*\n?', '', text)
        text = re.sub(r'\n?```\s*$',          '', text)

        result = json.loads(text)
        return jsonify(result)

    except json.JSONDecodeError:
        return jsonify({'error': 'Could not parse bill JSON. Try a clearer photo.'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ─────────────────────────────────────────────
#  ENTRY POINT
# ─────────────────────────────────────────────
if __name__ == '__main__':
    port  = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('DEBUG', 'false').lower() == 'true'
    print(f"\n  SplitBill running at http://localhost:{port}")
    if HAS_AI and os.environ.get('GEMINI_API_KEY', '').strip():
        print("  AI photo scanning: enabled")
    else:
        print("  AI photo scanning: disabled (no GEMINI_API_KEY)")
    print()
    app.run(host='0.0.0.0', port=port, debug=debug)
