/**
 * MedWriter API Client
 * Handles all API communication
 */

const API_BASE = window.location.origin + '/api';

class MedWriterAPI {
    /**
     * List all conversations
     */
    static async listConversations(skip = 0, limit = 50) {
        const response = await fetch(`${API_BASE}/conversations?skip=${skip}&limit=${limit}`);

        if (!response.ok) {
            throw new Error('Nie udało się pobrać listy rozmów');
        }

        return await response.json();
    }

    /**
     * Get conversation details with messages
     */
    static async getConversation(convId) {
        if (!convId || convId === 'null' || convId === 'undefined') {
            throw new Error('Invalid conversation ID');
        }

        const response = await fetch(`${API_BASE}/conversations/${convId}`);

        if (!response.ok) {
            throw new Error('Nie udało się pobrać rozmowy');
        }

        return await response.json();
    }

    /**
     * Create new conversation
     */
    static async createConversation(title = null) {
        const response = await fetch(`${API_BASE}/conversations`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ title })
        });

        if (!response.ok) {
            throw new Error('Nie udało się utworzyć rozmowy');
        }

        return await response.json();
    }

    /**
     * Delete conversation
     */
    static async deleteConversation(convId) {
        const response = await fetch(`${API_BASE}/conversations/${convId}`, {
            method: 'DELETE'
        });

        if (!response.ok) {
            throw new Error('Nie udało się usunąć rozmowy');
        }
    }

    /**
     * Get messages for conversation
     */
    static async getMessages(convId) {
        const response = await fetch(`${API_BASE}/conversations/${convId}/messages`);

        if (!response.ok) {
            throw new Error('Nie udało się pobrać wiadomości');
        }

        return await response.json();
    }

    /**
     * Send message with optional PDF files (creates job)
     * @param {string} convId - Conversation ID
     * @param {string} content - Message text
     * @param {FileList|Array} files - Optional PDF files
     */
    static async sendMessage(convId, content, files = []) {
        if (!convId || convId === 'null' || convId === 'undefined') {
            throw new Error('Invalid conversation ID');
        }

        const formData = new FormData();
        formData.append('content', content);
        for (const file of files) {
            formData.append('files', file);
        }

        const response = await fetch(`${API_BASE}/conversations/${convId}/messages`, {
            method: 'POST',
            body: formData,
        });

        if (!response.ok) {
            throw new Error('Nie udało się wysłać wiadomości');
        }

        return await response.json();
    }

    /**
     * Get job status
     */
    static async getJobStatus(jobId) {
        const response = await fetch(`${API_BASE}/jobs/${jobId}/status`);

        if (!response.ok) {
            throw new Error('Nie udało się pobrać statusu zadania');
        }

        return await response.json();
    }

    /**
     * Poll job status until complete
     * @param {string} jobId - Job ID to poll
     * @param {function} onStatusChange - Callback for status changes
     * @param {number} maxAttempts - Maximum polling attempts (default 120 = 2 minutes)
     */
    static async pollJobStatus(jobId, onStatusChange = null, maxAttempts = 120) {
        let attempts = 0;

        while (attempts < maxAttempts) {
            attempts++;

            try {
                const status = await this.getJobStatus(jobId);

                if (onStatusChange) {
                    onStatusChange(status);
                }

                if (status.status === 'Ready') {
                    return status;
                }

                // Wait before next poll
                await new Promise(resolve => setTimeout(resolve, 1000));

            } catch (error) {
                console.error('Error polling job status:', error);
                throw error;
            }
        }

        throw new Error('Timeout: Zadanie nie zostało ukończone w czasie');
    }
}

// Utility functions
function formatDate(dateString) {
    const date = new Date(dateString);
    const now = new Date();
    const diff = now - date;

    // Less than 1 minute
    if (diff < 60000) {
        return 'przed chwilą';
    }

    // Less than 1 hour
    if (diff < 3600000) {
        const minutes = Math.floor(diff / 60000);
        return `${minutes} ${minutes === 1 ? 'minutę' : 'minut'} temu`;
    }

    // Less than 24 hours
    if (diff < 86400000) {
        const hours = Math.floor(diff / 3600000);
        return `${hours} ${hours === 1 ? 'godzinę' : 'godzin'} temu`;
    }

    // Format as date
    return date.toLocaleDateString('pl-PL', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

function pluralize(count, singular, plural, genitive) {
    if (count === 1) return singular;
    if (count % 10 >= 2 && count % 10 <= 4 && (count % 100 < 10 || count % 100 >= 20)) {
        return plural;
    }
    return genitive;
}
