import type { APIRequestContext } from '@playwright/test';

// Used by the browser tests to prepare data and to check postconditions
// (request status, used_days, request count) directly against the API, so a
// test does not rely only on what the screen says.

export type Role = 'employee' | 'other' | 'admin';

export const ACCOUNTS: Record<Role, { email: string; password: string; name: string }> = {
  employee: { email: 'demo@leavedesk.in', password: 'demo1234', name: 'Ananya Rao' },
  other: { email: 'rohan.iyer@leavedesk.in', password: 'demo1234', name: 'Rohan Iyer' },
  admin: { email: 'admin@leavedesk.in', password: 'admin1234', name: 'Aarav Mehta' },
};

export const API_URL = process.env.API_URL ?? 'http://localhost:5001';

export interface Reply<T = any> {
  status: number;
  body: T;
}

export interface NewRequest {
  type: 'CASUAL' | 'SICK' | 'EARNED';
  start: string;
  end: string;
  reason: string;
}

export class LeaveApi {
  private tokens = new Map<Role, string>();
  private typeIds = new Map<string, number>();
  private created: { role: Role; id: number }[] = [];

  constructor(public readonly http: APIRequestContext) {}

  async token(role: Role): Promise<string> {
    const cached = this.tokens.get(role);
    if (cached) return cached;
    const reply = await this.raw('POST', '/api/auth/login', undefined, ACCOUNTS[role]);
    if (reply.status !== 200) throw new Error(`login failed for ${role}: ${reply.status}`);
    this.tokens.set(role, reply.body.access_token);
    return reply.body.access_token;
  }

  async raw(method: string, path: string, token?: string, data?: unknown): Promise<Reply> {
    const response = await this.http.fetch(API_URL + path, {
      method,
      data: data as any,
      headers: token ? { Authorization: `Bearer ${token}` } : undefined,
    });
    let body: any = null;
    try {
      body = await response.json();
    } catch {
      body = await response.text();
    }
    return { status: response.status(), body };
  }

  async call(role: Role, method: string, path: string, data?: unknown): Promise<Reply> {
    return this.raw(method, path, await this.token(role), data);
  }

  async typeId(code: string): Promise<number> {
    if (!this.typeIds.size) {
      const reply = await this.call('employee', 'GET', '/api/leave-types');
      for (const item of reply.body.leave_types) this.typeIds.set(item.code, item.id);
    }
    return this.typeIds.get(code)!;
  }

  /** used_days for one leave type and year, read back from the API. */
  async usedDays(role: Role, code: string, year: number): Promise<number> {
    const reply = await this.call(role, 'GET', `/api/leave-balances?year=${year}`);
    const row = reply.body.balances.find((b: any) => b.leave_type.code === code);
    return row.used_days;
  }

  async remainingDays(role: Role, code: string, year: number): Promise<number> {
    const reply = await this.call(role, 'GET', `/api/leave-balances?year=${year}`);
    return reply.body.balances.find((b: any) => b.leave_type.code === code).remaining_days;
  }

  /** All requests of the signed-in user that start inside the given year. */
  async requestsInYear(role: Role, year: number): Promise<any[]> {
    const reply = await this.call(role, 'GET', `/api/leave-requests?year=${year}&per_page=50`);
    return reply.body.items;
  }

  async find(role: Role, start: string, end: string): Promise<any[]> {
    const year = Number(start.slice(0, 4));
    return (await this.requestsInYear(role, year)).filter(
      (r) => r.start_date === start && r.end_date === end,
    );
  }

  async get(role: Role, id: number): Promise<Reply> {
    return this.call(role, 'GET', `/api/leave-requests/${id}`);
  }

  /** Create a request through the API (test setup). It is cancelled again after the test. */
  async create(role: Role, req: NewRequest): Promise<any> {
    const reply = await this.call(role, 'POST', '/api/leave-requests', {
      leave_type_id: await this.typeId(req.type),
      start_date: req.start,
      end_date: req.end,
      reason: req.reason,
    });
    if (reply.status !== 201) {
      throw new Error(`setup request failed: ${reply.status} ${JSON.stringify(reply.body)}`);
    }
    this.track(role, reply.body.id);
    return reply.body;
  }

  track(role: Role, id: number) {
    this.created.push({ role, id });
  }

  async review(id: number, decision: 'approve' | 'reject', note?: string): Promise<Reply> {
    return this.call('admin', 'POST', `/api/leave-requests/${id}/review`, { decision, note });
  }

  async cancel(role: Role, id: number): Promise<Reply> {
    return this.call(role, 'POST', `/api/leave-requests/${id}/cancel`);
  }

  /** Put the data back: cancel every request this test made that is still open. */
  async cleanup() {
    for (const { role, id } of this.created.reverse()) {
      const current = await this.get(role, id);
      if (current.status === 200 && ['pending', 'approved'].includes(current.body.status)) {
        await this.cancel(role, id);
      }
    }
    this.created = [];
  }

  /** Remember requests that the browser created, found by their start date. */
  async trackByDates(role: Role, start: string, end: string) {
    for (const item of await this.find(role, start, end)) this.track(role, item.id);
  }
}
