import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi } from 'vitest';
import { MessageInput } from '../MessageInput';

describe('MessageInput', () => {
  it('renders with default placeholder', () => {
    render(<MessageInput onSend={vi.fn()} />);
    expect(screen.getByPlaceholderText('Message Nebulus...')).toBeInTheDocument();
  });

  it('renders with custom placeholder', () => {
    render(<MessageInput onSend={vi.fn()} placeholder="Ask anything..." />);
    expect(screen.getByPlaceholderText('Ask anything...')).toBeInTheDocument();
  });

  it('calls onSend with trimmed content on button click', async () => {
    const user = userEvent.setup();
    const onSend = vi.fn();
    render(<MessageInput onSend={onSend} />);

    await user.type(screen.getByRole('textbox'), '  Hello world  ');
    await user.click(screen.getByRole('button', { name: 'Send message' }));

    expect(onSend).toHaveBeenCalledWith('Hello world');
  });

  it('clears input after sending', async () => {
    const user = userEvent.setup();
    render(<MessageInput onSend={vi.fn()} />);

    const input = screen.getByRole('textbox');
    await user.type(input, 'Hello');
    await user.click(screen.getByRole('button', { name: 'Send message' }));

    expect(input).toHaveValue('');
  });

  it('sends on Enter key', async () => {
    const user = userEvent.setup();
    const onSend = vi.fn();
    render(<MessageInput onSend={onSend} />);

    await user.type(screen.getByRole('textbox'), 'Hello{Enter}');
    expect(onSend).toHaveBeenCalledWith('Hello');
  });

  it('does not send on Shift+Enter', async () => {
    const user = userEvent.setup();
    const onSend = vi.fn();
    render(<MessageInput onSend={onSend} />);

    await user.type(screen.getByRole('textbox'), 'Hello{Shift>}{Enter}{/Shift}');
    expect(onSend).not.toHaveBeenCalled();
  });

  it('does not send empty/whitespace-only messages', async () => {
    const user = userEvent.setup();
    const onSend = vi.fn();
    render(<MessageInput onSend={onSend} />);

    await user.click(screen.getByRole('button', { name: 'Send message' }));
    expect(onSend).not.toHaveBeenCalled();

    await user.type(screen.getByRole('textbox'), '   ');
    await user.click(screen.getByRole('button', { name: 'Send message' }));
    expect(onSend).not.toHaveBeenCalled();
  });

  it('disables input and button when disabled prop is true', () => {
    render(<MessageInput onSend={vi.fn()} disabled />);
    expect(screen.getByRole('textbox')).toBeDisabled();
    expect(screen.getByText('Generating response...')).toBeInTheDocument();
  });

  it('does not send when disabled', async () => {
    const onSend = vi.fn();
    render(<MessageInput onSend={onSend} disabled />);

    // Can't type into disabled textarea, but verify button is disabled
    expect(screen.getByRole('button', { name: 'Send message' })).toBeDisabled();
  });
});
