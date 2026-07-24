import React from 'react';
import { render, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter as BR } from 'react-router-dom';
import App from './App';

describe('App', () => {
  it('renders HomePage', async () => {
    const { getByText } = render(<BR><App /></BR>);
    await waitFor(() => getByText('Auto-Forge Generated App'));
    expect(getByText('Auto-Forge Generated App')).toBeInTheDocument();
  });

  it('does not render FEATURE_LINKS_START or FEATURE_LINKS_END', async () => {
    const { queryByRole } = render(<BR><App /></BR>);
    await waitFor(() => queryByRole('listitem'));
    expect(queryByRole('listitem')).not.toBeInTheDocument();
  });
});