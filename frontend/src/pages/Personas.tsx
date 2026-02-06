import { useState, useEffect } from 'react';
import { usePersonaStore } from '../stores/personaStore';
import type { Persona, CreatePersonaRequest } from '../types/api';

export function Personas() {
  const { personas, isLoading, fetchPersonas, createPersona, updatePersona, deletePersona } =
    usePersonaStore();

  const [showModal, setShowModal] = useState(false);
  const [editingPersona, setEditingPersona] = useState<Persona | null>(null);
  const [formData, setFormData] = useState<CreatePersonaRequest>({
    name: '',
    description: '',
    system_prompt: '',
    temperature: 0.7,
  });
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    fetchPersonas();
  }, [fetchPersonas]);

  const userPersonas = personas.filter((p) => !p.is_system);

  const openCreateModal = () => {
    setEditingPersona(null);
    setFormData({
      name: '',
      description: '',
      system_prompt: '',
      temperature: 0.7,
    });
    setShowModal(true);
  };

  const openEditModal = (persona: Persona) => {
    setEditingPersona(persona);
    setFormData({
      name: persona.name,
      description: persona.description || '',
      system_prompt: persona.system_prompt,
      temperature: persona.temperature,
    });
    setShowModal(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.name.trim() || !formData.system_prompt.trim()) return;

    setIsSaving(true);
    try {
      if (editingPersona) {
        await updatePersona(editingPersona.id, formData);
      } else {
        await createPersona(formData);
      }
      setShowModal(false);
    } catch {
      // Error handled in store
    } finally {
      setIsSaving(false);
    }
  };

  const handleDelete = async (id: number) => {
    if (!window.confirm('Delete this persona?')) return;
    try {
      await deletePersona(id);
    } catch {
      // Error handled in store
    }
  };

  return (
    <div className="flex-1 overflow-y-auto p-6">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold text-white">Personas</h1>
            <p className="text-gray-400 text-sm mt-1">
              Create custom personas with specific system prompts and preferences
            </p>
          </div>
          <button
            onClick={openCreateModal}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            New Persona
          </button>
        </div>

        {/* Personas Grid */}
        {isLoading && userPersonas.length === 0 ? (
          <div className="flex justify-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
          </div>
        ) : userPersonas.length === 0 ? (
          <div className="text-center py-12">
            <div className="text-gray-500 text-lg mb-4">No personas yet</div>
            <p className="text-gray-600 text-sm mb-6">
              Create a persona to customize how the AI responds to you
            </p>
            <button
              onClick={openCreateModal}
              className="inline-flex items-center gap-2 px-4 py-2 bg-gray-800 hover:bg-gray-700 text-gray-300 rounded-lg transition-colors"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
              </svg>
              Create Your First Persona
            </button>
          </div>
        ) : (
          <div className="grid gap-4 md:grid-cols-2">
            {userPersonas.map((persona) => (
              <div
                key={persona.id}
                className="bg-gray-800 border border-gray-700 rounded-lg p-4 hover:border-gray-600 transition-colors"
              >
                <div className="flex items-start justify-between mb-2">
                  <h3 className="text-lg font-medium text-white">{persona.name}</h3>
                  <div className="flex gap-1">
                    <button
                      onClick={() => openEditModal(persona)}
                      className="p-1.5 text-gray-400 hover:text-white hover:bg-gray-700 rounded"
                      title="Edit persona"
                    >
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                      </svg>
                    </button>
                    <button
                      onClick={() => handleDelete(persona.id)}
                      className="p-1.5 text-gray-400 hover:text-red-400 hover:bg-gray-700 rounded"
                      title="Delete persona"
                    >
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                      </svg>
                    </button>
                  </div>
                </div>

                {persona.description && (
                  <p className="text-gray-400 text-sm mb-3">{persona.description}</p>
                )}

                <div className="text-xs text-gray-500 space-y-1">
                  <div className="flex items-center gap-2">
                    <span>Temperature:</span>
                    <span className="text-gray-400">{persona.temperature}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span>Prompt preview:</span>
                  </div>
                  <p className="text-gray-400 line-clamp-2 bg-gray-900 rounded px-2 py-1">
                    {persona.system_prompt}
                  </p>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Modal */}
        {showModal && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <div className="bg-gray-800 border border-gray-700 rounded-lg w-full max-w-lg max-h-[90vh] overflow-y-auto">
              <form onSubmit={handleSubmit}>
                <div className="p-4 border-b border-gray-700">
                  <h2 className="text-lg font-medium text-white">
                    {editingPersona ? 'Edit Persona' : 'Create Persona'}
                  </h2>
                </div>

                <div className="p-4 space-y-4">
                  {/* Name */}
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-1">
                      Name
                    </label>
                    <input
                      type="text"
                      value={formData.name}
                      onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                      className="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded-lg text-gray-200 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
                      placeholder="e.g., Coding Assistant"
                      required
                    />
                  </div>

                  {/* Description */}
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-1">
                      Description (optional)
                    </label>
                    <input
                      type="text"
                      value={formData.description}
                      onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                      className="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded-lg text-gray-200 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
                      placeholder="Brief description"
                    />
                  </div>

                  {/* System Prompt */}
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-1">
                      System Prompt
                    </label>
                    <textarea
                      value={formData.system_prompt}
                      onChange={(e) => setFormData({ ...formData, system_prompt: e.target.value })}
                      rows={6}
                      className="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded-lg text-gray-200 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
                      placeholder="You are a helpful assistant..."
                      required
                    />
                  </div>

                  {/* Temperature */}
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-1">
                      Temperature: {formData.temperature}
                    </label>
                    <input
                      type="range"
                      min="0"
                      max="2"
                      step="0.1"
                      value={formData.temperature}
                      onChange={(e) => setFormData({ ...formData, temperature: parseFloat(e.target.value) })}
                      className="w-full"
                    />
                    <div className="flex justify-between text-xs text-gray-500">
                      <span>Precise</span>
                      <span>Creative</span>
                    </div>
                  </div>
                </div>

                <div className="p-4 border-t border-gray-700 flex justify-end gap-2">
                  <button
                    type="button"
                    onClick={() => setShowModal(false)}
                    className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-gray-300 rounded-lg transition-colors"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={isSaving}
                    className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors disabled:opacity-50"
                  >
                    {isSaving ? 'Saving...' : editingPersona ? 'Update' : 'Create'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
