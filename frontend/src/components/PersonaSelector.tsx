import { useState, useEffect, useRef } from 'react';
import { usePersonaStore } from '../stores/personaStore';
import type { Persona } from '../types/api';

interface PersonaSelectorProps {
  conversationId: number | null;
  currentPersonaId: number | null;
  currentPersonaName: string | null;
  onPersonaChange?: (persona: Persona | null) => void;
}

export function PersonaSelector({
  conversationId,
  currentPersonaId,
  currentPersonaName,
  onPersonaChange,
}: PersonaSelectorProps) {
  const { personas, fetchPersonas, setConversationPersona } = usePersonaStore();
  const [isOpen, setIsOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (isOpen && personas.length === 0) {
      fetchPersonas();
    }
  }, [isOpen, personas.length, fetchPersonas]);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleSelectPersona = async (persona: Persona | null) => {
    if (!conversationId) return;

    setIsLoading(true);
    try {
      await setConversationPersona(conversationId, persona?.id ?? null);
      onPersonaChange?.(persona);
    } catch {
      // Error handled in store
    } finally {
      setIsLoading(false);
      setIsOpen(false);
    }
  };

  const displayName = currentPersonaName || 'Default';

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        className="flex items-center gap-1.5 px-2 py-1 text-xs bg-gray-800 hover:bg-gray-700 text-gray-300 rounded border border-gray-700 transition-colors disabled:opacity-50"
        onClick={() => setIsOpen(!isOpen)}
        disabled={!conversationId || isLoading}
        title="Select persona"
      >
        <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
        </svg>
        <span className="max-w-24 truncate">{displayName}</span>
        <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {isOpen && (
        <div className="absolute right-0 mt-1 w-64 bg-gray-800 border border-gray-700 rounded-lg shadow-lg z-50 max-h-64 overflow-y-auto">
          {/* Default option */}
          <button
            className={`w-full text-left px-3 py-2 text-sm hover:bg-gray-700 transition-colors ${
              currentPersonaId === null ? 'bg-gray-700 text-white' : 'text-gray-300'
            }`}
            onClick={() => handleSelectPersona(null)}
          >
            <div className="font-medium">Default</div>
            <div className="text-xs text-gray-500">Use default system prompt</div>
          </button>

          {personas.length > 0 && <div className="border-t border-gray-700" />}

          {/* System personas */}
          {personas.filter((p) => p.is_system).length > 0 && (
            <>
              <div className="px-3 py-1 text-xs font-medium text-gray-500 uppercase">System</div>
              {personas
                .filter((p) => p.is_system)
                .map((persona) => (
                  <button
                    key={persona.id}
                    className={`w-full text-left px-3 py-2 text-sm hover:bg-gray-700 transition-colors ${
                      currentPersonaId === persona.id ? 'bg-gray-700 text-white' : 'text-gray-300'
                    }`}
                    onClick={() => handleSelectPersona(persona)}
                  >
                    <div className="font-medium">{persona.name}</div>
                    {persona.description && (
                      <div className="text-xs text-gray-500 truncate">{persona.description}</div>
                    )}
                  </button>
                ))}
            </>
          )}

          {/* User personas */}
          {personas.filter((p) => !p.is_system).length > 0 && (
            <>
              <div className="px-3 py-1 text-xs font-medium text-gray-500 uppercase">My Personas</div>
              {personas
                .filter((p) => !p.is_system)
                .map((persona) => (
                  <button
                    key={persona.id}
                    className={`w-full text-left px-3 py-2 text-sm hover:bg-gray-700 transition-colors ${
                      currentPersonaId === persona.id ? 'bg-gray-700 text-white' : 'text-gray-300'
                    }`}
                    onClick={() => handleSelectPersona(persona)}
                  >
                    <div className="font-medium">{persona.name}</div>
                    {persona.description && (
                      <div className="text-xs text-gray-500 truncate">{persona.description}</div>
                    )}
                  </button>
                ))}
            </>
          )}

          {personas.length === 0 && (
            <div className="px-3 py-4 text-center text-sm text-gray-500">
              No personas available
            </div>
          )}
        </div>
      )}
    </div>
  );
}
