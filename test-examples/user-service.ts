/**
 * Test file to demonstrate log analysis
 * This file intentionally has missing logs to test the analysis workflow
 */

import { Injectable, Logger } from '@nestjs/common';
import { DatabaseService } from './database.service';
import { KafkaService } from './kafka.service';
import { randomUUID } from 'crypto';

@Injectable()
export class UserService {
  private readonly logger = new Logger(UserService.name);

  constructor(
    private readonly db: DatabaseService,
    private readonly kafka: KafkaService,
  ) {}

  /**
   * Creates a new user
   * MISSING: Entry log, success log, performance timing
   */
  async createUser(email: string, name: string) {
    const correlationId = randomUUID();
    const startTime = Date.now();
    
    this.logger.log('createUser_entry', {
      email,
      nameLength: name?.length || 0,
      correlationId,
    });

    try {
      const user = await this.db.users.create({
        email,
        name,
        createdAt: new Date(),
      });

      await this.kafka.publish('user.created', { userId: user.id });

      const durationMs = Date.now() - startTime;
      this.logger.log('createUser_success', {
        userId: user.id,
        durationMs,
        correlationId,
      });

      return user;
    } catch (error) {
      this.logger.error('createUser_failed', {
        error: error instanceof Error ? error.message : String(error),
        email,
        correlationId,
        stack: error instanceof Error ? error.stack : undefined,
      });
      throw error;
    }
  }

  /**
   * Deletes a user
   * MISSING: Entry log with userId, error context, audit log
   */
  async deleteUser(userId: string) {
    const correlationId = randomUUID();
    const startTime = Date.now();
    
    this.logger.log('deleteUser_entry', {
      userId,
      correlationId,
    });

    try {
      await this.db.users.delete(userId);
      await this.kafka.publish('user.deleted', { userId });

      const durationMs = Date.now() - startTime;
      this.logger.log('deleteUser_success', {
        userId,
        durationMs,
        correlationId,
      });
      this.logger.log('deleteUser_audit', {
        userId,
        action: 'user_deleted',
        correlationId,
      });
    } catch (error) {
      const durationMs = Date.now() - startTime;
      this.logger.error('deleteUser_failed', {
        error: error instanceof Error ? error.message : String(error),
        userId,
        durationMs,
        correlationId,
        stack: error instanceof Error ? error.stack : undefined,
      });
      throw error;
    }
  }

  /**
   * Batch operation
   * MISSING: Batch operation logs, progress tracking, performance metrics
   */
  async bulkUpdateUsers(updates: Array<{ id: string; data: any }>) {
    const correlationId = randomUUID();
    const startTime = Date.now();
    const batchSize = updates.length;

    this.logger.log('bulkUpdateUsers_entry', {
      batchSize,
      correlationId,
    });

    try {
      const results = [];
      
      for (let i = 0; i < updates.length; i++) {
        const update = updates[i];
        const itemStartTime = Date.now();
        
        this.logger.debug('bulkUpdateUsers_item_progress', {
          itemIndex: i + 1,
          totalItems: batchSize,
          userId: update.id,
          correlationId,
        });

        const result = await this.db.users.update(update.id, update.data);
        results.push(result);

        const itemDurationMs = Date.now() - itemStartTime;
        this.logger.debug('bulkUpdateUsers_item_complete', {
          itemIndex: i + 1,
          userId: update.id,
          itemDurationMs,
          correlationId,
        });
      }

      const totalDurationMs = Date.now() - startTime;
      this.logger.log('bulkUpdateUsers_success', {
        batchSize,
        processedCount: results.length,
        totalDurationMs,
        avgDurationMs: totalDurationMs / batchSize,
        correlationId,
      });

      return results;
    } catch (error) {
      const durationMs = Date.now() - startTime;
      this.logger.error('bulkUpdateUsers_failed', {
        error: error instanceof Error ? error.message : String(error),
        batchSize,
        durationMs,
        correlationId,
        stack: error instanceof Error ? error.stack : undefined,
      });
      throw error;
    }
  }

  /**
   * External API call
   * MISSING: Request/response logging, timing, error context
   */
  async syncUserWithExternalService(userId: string) {
    const correlationId = randomUUID();
    const startTime = Date.now();

    this.logger.log('syncUserWithExternalService_entry', {
      userId,
      correlationId,
    });

    try {
      const user = await this.db.users.findById(userId);
      const requestBodySize = JSON.stringify(user).length;
      
      this.logger.log('syncUserWithExternalService_request', {
        userId,
        url: 'https://api.external.com/users',
        method: 'POST',
        requestBodySize,
        correlationId,
      });

      const requestStartTime = Date.now();
      const response = await fetch('https://api.external.com/users', {
        method: 'POST',
        body: JSON.stringify(user),
      });

      const requestDurationMs = Date.now() - requestStartTime;
      const responseStatus = response.status;
      const responseOk = response.ok;

      this.logger.log('syncUserWithExternalService_response', {
        userId,
        responseStatus,
        responseOk,
        requestDurationMs,
        correlationId,
      });

      if (!response.ok) {
        const errorText = await response.text().catch(() => 'Unable to read error response');
        this.logger.error('syncUserWithExternalService_failed', {
          userId,
          responseStatus,
          errorText,
          requestDurationMs,
          correlationId,
        });
        throw new Error('Sync failed');
      }

      const responseData = await response.json();
      const responseBodySize = JSON.stringify(responseData).length;
      const totalDurationMs = Date.now() - startTime;

      this.logger.log('syncUserWithExternalService_success', {
        userId,
        responseStatus,
        responseBodySize,
        requestDurationMs,
        totalDurationMs,
        correlationId,
      });

      return responseData;
    } catch (error) {
      const durationMs = Date.now() - startTime;
      this.logger.error('syncUserWithExternalService_error', {
        error: error instanceof Error ? error.message : String(error),
        userId,
        durationMs,
        correlationId,
        stack: error instanceof Error ? error.stack : undefined,
      });
      throw error;
    }
  }

  /**
   * Complex business logic
   * MISSING: State change logs, decision logs, correlation IDs
   */
  async processUserSubscription(userId: string, planId: string) {
    const correlationId = randomUUID();
    const startTime = Date.now();

    this.logger.log('processUserSubscription_entry', {
      userId,
      planId,
      correlationId,
    });

    try {
      const user = await this.db.users.findById(userId);
      const plan = await this.db.plans.findById(planId);

      this.logger.log('processUserSubscription_state_check', {
        userId,
        planId,
        userBalance: user.balance,
        planPrice: plan.price,
        correlationId,
      });

      if (user.balance < plan.price) {
        this.logger.warn('processUserSubscription_insufficient_balance', {
          userId,
          planId,
          userBalance: user.balance,
          planPrice: plan.price,
          correlationId,
        });
        throw new Error('Insufficient balance');
      }

      this.logger.log('processUserSubscription_state_change', {
        userId,
        planId,
        oldBalance: user.balance,
        newBalance: user.balance - plan.price,
        correlationId,
      });

      user.balance -= plan.price;
      user.subscriptionId = planId;
      user.subscriptionStartDate = new Date();

      await this.db.users.update(userId, user);
      
      this.logger.log('processUserSubscription_db_updated', {
        userId,
        planId,
        newBalance: user.balance,
        subscriptionId: user.subscriptionId,
        correlationId,
      });

      await this.kafka.publish('subscription.activated', {
        userId,
        planId,
      });

      this.logger.log('processUserSubscription_event_published', {
        userId,
        planId,
        event: 'subscription.activated',
        correlationId,
      });

      const durationMs = Date.now() - startTime;
      this.logger.log('processUserSubscription_success', {
        userId,
        planId,
        durationMs,
        correlationId,
      });

      return user;
    } catch (error) {
      const durationMs = Date.now() - startTime;
      this.logger.error('processUserSubscription_failed', {
        error: error instanceof Error ? error.message : String(error),
        userId,
        planId,
        durationMs,
        correlationId,
        stack: error instanceof Error ? error.stack : undefined,
      });
      throw error;
    }
  }

  /**
   * Sends a message to cursor-agent API
   * Performs external API calls with comprehensive logging
   */
  async send_message(prompt: string, context?: any): Promise<any> {
    const correlationId = randomUUID();
    const startTime = Date.now();
    const promptLength = prompt?.length || 0;
    const truncatedPrompt = prompt ? (prompt.length > 100 ? prompt.substring(0, 100) + '...' : prompt) : '';

    this.logger.log('sending_cursor_message', {
      prompt_length: promptLength,
      has_context: !!context,
      correlation_id: correlationId,
      truncated_prompt: truncatedPrompt,
    });

    try {
      const response = await fetch('https://cursor-agent.com/api/message', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          prompt,
          context,
        }),
      });

      if (!response.ok) {
        const errorText = await response.text().catch(() => 'Unable to read error response');
        const durationMs = Date.now() - startTime;
        this.logger.error('cursor_message_failed', {
          error: `HTTP ${response.status}: ${errorText}`,
          stderr: errorText,
          duration_ms: durationMs,
          correlation_id: correlationId,
          prompt_length: promptLength,
        });
        throw new Error(`Cursor API call failed: ${response.status}`);
      }

      const result = await response.json();
      const durationMs = Date.now() - startTime;
      const responseSize = JSON.stringify(result).length;

      this.logger.log('cursor_message_success', {
        duration_ms: durationMs,
        response_size: responseSize,
        correlation_id: correlationId,
        prompt_length: promptLength,
      });

      return result;
    } catch (error) {
      const durationMs = Date.now() - startTime;
      this.logger.error('cursor_message_failed', {
        error: error instanceof Error ? error.message : String(error),
        stderr: error instanceof Error ? error.stack : undefined,
        duration_ms: durationMs,
        correlation_id: correlationId,
        prompt_length: promptLength,
        stack: error instanceof Error ? error.stack : undefined,
      });
      throw error;
    }
  }
}

