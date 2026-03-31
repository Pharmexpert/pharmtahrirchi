"use client";

import React, { useState, useEffect } from 'react';
import { 
  ArrowLeft, 
  Trash2, 
  Edit2, 
  Plus, 
  Search, 
  BookOpen, 
  RefreshCcw,
  Languages,
  CheckCircle2,
  AlertCircle
} from 'lucide-react';
import Link from 'next/link';

interface Rule {
  id: number;
  wrong_form: string;
  correct_form: string;
  error_type: string;
  lang: string;
  frequency: number;
  updated_at: string;
}

export default function RulesPage() {
  const [rules, setRules] = useState<Rule[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [lang, setLang] = useState("uz");
  const [editingRule, setEditingRule] = useState<Partial<Rule> | null>(null);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' } | null>(null);

  const API_BASE = (typeof window !== 'undefined' && (window as any).NEXT_PUBLIC_API_URL) || "http://localhost:8000";

  useEffect(() => {
    fetchRules();
  }, [lang]);

  const fetchRules = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/sayqallash-rules?lang=${lang}&limit=500`);
      const data = await res.json();
      setRules(data.rules || []);
    } catch (err) {
      console.error("Failed to fetch rules:", err);
    } finally {
      setLoading(false);
    }
  };

  const showMessage = (text: string, type: 'success' | 'error' = 'success') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 3000);
  };

  const handleDelete = async (id: number) => {
    if (!confirm("Are you sure you want to delete this rule?")) return;
    try {
      const res = await fetch(`${API_BASE}/sayqallash-rules/${id}`, { method: 'DELETE' });
      if (res.ok) {
        setRules(rules.filter(r => r.id !== id));
        showMessage("Rule deleted successfully");
      }
    } catch (err) {
      showMessage("Failed to delete rule", "error");
    }
  };

  const handleSave = async () => {
    if (!editingRule?.wrong_form || !editingRule?.correct_form) return;

    const isNew = !editingRule.id;
    const url = isNew ? `${API_BASE}/sayqallash-rules` : `${API_BASE}/sayqallash-rules/${editingRule.id}`;
    const method = isNew ? 'POST' : 'PUT';

    try {
      const res = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...editingRule,
          lang // ensure language is preserved
        })
      });

      if (res.ok) {
        fetchRules();
        setEditingRule(null);
        showMessage(isNew ? "Rule added" : "Rule updated");
      }
    } catch (err) {
      showMessage("Save failed", "error");
    }
  };

  const filteredRules = rules.filter(r => 
    r.wrong_form.toLowerCase().includes(search.toLowerCase()) || 
    r.correct_form.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 font-sans">
      {/* Header */}
      <header className="bg-white border-b border-slate-200 sticky top-0 z-10 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 h-16 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link href="/" className="p-2 hover:bg-slate-100 rounded-full transition-colors">
              <ArrowLeft className="w-5 h-5 text-slate-600" />
            </Link>
            <div className="flex items-center gap-2">
              <div className="w-10 h-10 bg-indigo-600 rounded-xl flex items-center justify-center shadow-lg shadow-indigo-200">
                <BookOpen className="w-5 h-5 text-white" />
              </div>
              <h1 className="text-xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-slate-900 to-indigo-600">
                Correction Database
              </h1>
            </div>
          </div>
          
          <div className="flex items-center gap-3">
            <div className="flex bg-slate-100 p-1 rounded-lg">
              <button 
                onClick={() => setLang('uz')}
                className={`px-4 py-1.5 rounded-md text-sm font-medium transition-all ${lang === 'uz' ? 'bg-white shadow-sm text-indigo-600' : 'text-slate-500 hover:text-slate-700'}`}
              >
                O'zbekcha
              </button>
              <button 
                onClick={() => setLang('ru')}
                className={`px-4 py-1.5 rounded-md text-sm font-medium transition-all ${lang === 'ru' ? 'bg-white shadow-sm text-indigo-600' : 'text-slate-500 hover:text-slate-700'}`}
              >
                Русский
              </button>
            </div>
            
            <button 
              onClick={() => setEditingRule({ wrong_form: '', correct_form: '', error_type: 'S/Spelling', lang })}
              className="bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded-lg text-sm font-semibold flex items-center gap-2 shadow-md transition-all active:scale-95"
            >
              <Plus className="w-4 h-4" />
              Add Rule
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-8">
        {/* Status Message */}
        {message && (
          <div className={`fixed bottom-8 right-8 flex items-center gap-3 px-5 py-4 rounded-2xl shadow-2xl animate-in fade-in slide-in-from-bottom-5 duration-300 z-50 ${message.type === 'success' ? 'bg-emerald-500 text-white' : 'bg-rose-500 text-white'}`}>
            {message.type === 'success' ? <CheckCircle2 className="w-5 h-5" /> : <AlertCircle className="w-5 h-5" />}
            <span className="font-medium">{message.text}</span>
          </div>
        )}

        {/* Search & Stats */}
        <div className="mb-8 flex flex-col md:flex-row gap-4 items-start md:items-center justify-between">
          <div className="relative w-full md:w-96">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <input 
              type="text" 
              placeholder="Search rules..."
              className="w-full pl-10 pr-4 py-2.5 bg-white border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all shadow-sm"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
          
          <div className="flex items-center gap-6 text-sm text-slate-500 bg-white px-6 py-2.5 rounded-xl border border-slate-100 shadow-sm">
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-indigo-500"></span>
              Total Rules: <span className="font-bold text-slate-900">{rules.length}</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
              Active
            </div>
            <button onClick={fetchRules} className="p-1 hover:bg-slate-100 rounded-lg transition-colors">
              <RefreshCcw className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Rules Table */}
        <div className="bg-white rounded-2xl border border-slate-200 shadow-xl shadow-slate-200/50 overflow-hidden">
          <table className="w-full border-collapse text-left">
            <thead>
              <tr className="bg-slate-50/50 border-b border-slate-200">
                <th className="px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-wider">Original (Wrong)</th>
                <th className="px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-wider">Correction (Correct)</th>
                <th className="px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-wider">Type</th>
                <th className="px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-wider text-center">Frequency</th>
                <th className="px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-wider text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {loading ? (
                Array.from({ length: 5 }).map((_, i) => (
                  <tr key={i} className="animate-pulse">
                    <td colSpan={5} className="px-6 py-6"><div className="h-4 bg-slate-100 rounded w-full"></div></td>
                  </tr>
                ))
              ) : filteredRules.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-6 py-20 text-center text-slate-400">
                    <div className="flex flex-col items-center gap-4">
                      <BookOpen className="w-12 h-12 text-slate-200" />
                      <p className="text-lg font-medium">No rules found</p>
                      <p className="text-sm">Try a different search or language</p>
                    </div>
                  </td>
                </tr>
              ) : (
                filteredRules.map((rule) => (
                  <tr key={rule.id} className="hover:bg-slate-50/50 transition-colors group">
                    <td className="px-6 py-4">
                      <span className="font-mono text-sm inline-block px-2 py-1 bg-rose-50 text-rose-700 rounded-md border border-rose-100">
                        {rule.wrong_form}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <span className="font-mono text-sm inline-block px-2 py-1 bg-emerald-50 text-emerald-700 rounded-md border border-emerald-100">
                        {rule.correct_form}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-slate-100 text-slate-600 border border-slate-200">
                        {rule.error_type}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-center">
                      <span className="text-sm font-bold text-indigo-600 bg-indigo-50 px-3 py-1 rounded-lg">
                        {rule.frequency}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-right">
                      <div className="flex items-center justify-end gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                        <button 
                          onClick={() => setEditingRule(rule)}
                          className="p-2 text-slate-400 hover:text-indigo-600 hover:bg-indigo-50 rounded-lg transition-all"
                        >
                          <Edit2 className="w-4 h-4" />
                        </button>
                        <button 
                          onClick={() => handleDelete(rule.id)}
                          className="p-2 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-lg transition-all"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </main>

      {/* Edit/Add Modal */}
      {editingRule && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-slate-900/40 backdrop-blur-sm animate-in fade-in duration-300" onClick={() => setEditingRule(null)}></div>
          <div className="bg-white rounded-3xl shadow-2xl max-w-lg w-full z-10 animate-in zoom-in-95 duration-200 overflow-hidden">
            <div className="px-8 py-6 border-b border-slate-100 flex items-center justify-between">
              <h2 className="text-xl font-bold text-slate-900">
                {editingRule.id ? 'Edit Correction Rule' : 'Add New Correction Rule'}
              </h2>
              <div className="flex items-center gap-2 text-xs font-bold text-slate-400 uppercase tracking-widest bg-slate-50 px-3 py-1 rounded-full">
                <Languages className="w-3 h-3" />
                {lang === 'uz' ? 'O\'zbekcha' : 'Русский'}
              </div>
            </div>
            
            <div className="p-8 space-y-6">
              <div className="space-y-2">
                <label className="text-sm font-bold text-slate-700 flex items-center gap-2">
                  <AlertCircle className="w-4 h-4 text-rose-500" />
                  Original Form (Incorrect)
                </label>
                <input 
                  type="text" 
                  value={editingRule.wrong_form}
                  onChange={e => setEditingRule({...editingRule, wrong_form: e.target.value})}
                  className="w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all font-mono text-sm"
                  placeholder="e.g. аниқлик"
                />
              </div>

              <div className="space-y-2">
                <label className="text-sm font-bold text-slate-700 flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                  Corrected Form
                </label>
                <input 
                  type="text" 
                  value={editingRule.correct_form}
                  onChange={e => setEditingRule({...editingRule, correct_form: e.target.value})}
                  className="w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all font-mono text-sm"
                  placeholder="e.g. аниқлиги"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <label className="text-sm font-bold text-slate-700">Type</label>
                  <select 
                    value={editingRule.error_type}
                    onChange={e => setEditingRule({...editingRule, error_type: e.target.value})}
                    className="w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all"
                  >
                    <option value="S/Spelling">Spelling</option>
                    <option value="S/Context">Context</option>
                    <option value="G/Grammar">Grammar</option>
                    <option value="Terminology">Terminology</option>
                  </select>
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-bold text-slate-700">Frequency</label>
                  <input 
                    type="number" 
                    value={editingRule.frequency || 1}
                    onChange={e => setEditingRule({...editingRule, frequency: parseInt(e.target.value)})}
                    className="w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all"
                  />
                </div>
              </div>
            </div>

            <div className="px-8 py-6 bg-slate-50 flex items-center justify-end gap-3">
              <button 
                onClick={() => setEditingRule(null)}
                className="px-6 py-2.5 rounded-xl text-sm font-bold text-slate-500 hover:text-slate-700 hover:bg-slate-100 transition-all"
              >
                Cancel
              </button>
              <button 
                onClick={handleSave}
                className="px-8 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-sm font-bold shadow-lg shadow-indigo-200 transition-all active:scale-95"
              >
                Save Changes
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
