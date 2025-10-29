/**
 * Test file to demonstrate log analysis
 * This file intentionally has missing logs to test the analysis workflow
 */

import { Injectable } from '@nestjs/common';
import { DatabaseService } from './database.service';
import { KafkaService } from './kafka.service';

@Injectable()
export class UserService {
  constructor(
    private readonly db: DatabaseService,
    private readonly kafka: KafkaService,
  ) {}

  /**
   * Creates a new user
   * MISSING: Entry log, success log, performance timing
   */
  async createUser(email: string, name: string) {
    const user = await this.db.users.create({
      email,
      name,
      createdAt: new Date(),
    });

    await this.kafka.publish('user.created', { userId: user.id });

    return user;
  }

  /**
   * Deletes a user
   * MISSING: Entry log with userId, error context, audit log
   */
  async deleteUser(userId: string) {
    try {
      await this.db.users.delete(userId);
      await this.kafka.publish('user.deleted', { userId });
    } catch (error) {
      throw error;
    }
  }

  /**
   * Batch operation
   * MISSING: Batch operation logs, progress tracking, performance metrics
   */
  async bulkUpdateUsers(updates: Array<{ id: string; data: any }>) {
    const results = [];
    
    for (const update of updates) {
      const result = await this.db.users.update(update.id, update.data);
      results.push(result);
    }

    return results;
  }

  /**
   * External API call
   * MISSING: Request/response logging, timing, error context
   */
  async syncUserWithExternalService(userId: string) {
    const user = await this.db.users.findById(userId);
    
    const response = await fetch('https://api.external.com/users', {
      method: 'POST',
      body: JSON.stringify(user),
    });

    if (!response.ok) {
      throw new Error('Sync failed');
    }

    return response.json();
  }

  /**
   * Complex business logic
   * MISSING: State change logs, decision logs, correlation IDs
   */
  async processUserSubscription(userId: string, planId: string) {
    const user = await this.db.users.findById(userId);
    const plan = await this.db.plans.findById(planId);

    if (user.balance < plan.price) {
      throw new Error('Insufficient balance');
    }

    user.balance -= plan.price;
    user.subscriptionId = planId;
    user.subscriptionStartDate = new Date();

    await this.db.users.update(userId, user);
    await this.kafka.publish('subscription.activated', {
      userId,
      planId,
    });

    return user;
  }
}

