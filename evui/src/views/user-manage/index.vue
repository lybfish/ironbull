<template>
  <div class="ele-body">
    <!-- 统计卡片 -->
    <el-row :gutter="15" style="margin-bottom: 15px;">
      <el-col :lg="6" :md="12" :sm="12">
        <stat-card
          title="总用户数"
          :value="stats.totalCount"
          icon="el-icon-user"
          color="primary"
          help-text="系统中的用户总数"
          :loading="statsLoading" />
      </el-col>
      <el-col :lg="6" :md="12" :sm="12">
        <stat-card
          title="今日新增"
          :value="stats.todayCount"
          icon="el-icon-user-solid"
          color="success"
          help-text="今日注册的用户数量"
          :loading="statsLoading" />
      </el-col>
      <el-col :lg="6" :md="12" :sm="12">
        <stat-card
          title="活跃用户"
          :value="stats.activeCount"
          icon="el-icon-star-on"
          color="warning"
          help-text="状态为正常的用户数量"
          :loading="statsLoading" />
      </el-col>
      <el-col :lg="6" :md="12" :sm="12">
        <stat-card
          title="总点卡余额"
          :value="stats.totalPointCard"
          icon="el-icon-bank-card"
          color="danger"
          format="money"
          :precision="2"
          help-text="所有用户的点卡总余额（自充+赠送）"
          :loading="statsLoading" />
      </el-col>
    </el-row>

    <!-- 主内容区 -->
    <el-card shadow="never">
      <!-- 搜索表单 -->
      <el-form :inline="true" :model="where" size="small" class="search-form">
        <el-form-item label="邮箱">
          <el-input
            v-model="where.email"
            placeholder="请输入邮箱"
            clearable
            style="width: 180px"
            @keyup.enter.native="reload" />
        </el-form-item>
        <el-form-item label="邀请码">
          <el-input
            v-model="where.invite_code"
            placeholder="请输入邀请码"
            clearable
            style="width: 140px"
            @keyup.enter.native="reload" />
        </el-form-item>
        <el-form-item label="邀请人ID">
          <el-input
            v-model="where.inviter_id"
            placeholder="请输入邀请人ID"
            clearable
            style="width: 120px"
            @keyup.enter.native="reload" />
        </el-form-item>
        <el-form-item label="自充点卡≥">
          <el-input
            v-model="where.point_card_self_min"
            placeholder="最小值"
            clearable
            style="width: 100px"
            @keyup.enter.native="reload" />
        </el-form-item>
        <el-form-item label="赠送点卡≥">
          <el-input
            v-model="where.point_card_gift_min"
            placeholder="最小值"
            clearable
            style="width: 100px"
            @keyup.enter.native="reload" />
        </el-form-item>
        <el-form-item label="租户">
          <el-select
            v-model="where.tenant_id"
            placeholder="全部租户"
            clearable
            filterable
            style="width: 140px">
            <el-option
              v-for="t in tenantList"
              :key="t.id"
              :label="t.name"
              :value="t.id" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" icon="el-icon-search" @click="reload">查询</el-button>
          <el-button @click="resetSearch">重置</el-button>
        </el-form-item>
      </el-form>

      <!-- 批量操作栏 -->
      <div v-if="selectedUsers.length > 0" style="margin-bottom: 10px; display: flex; align-items: center; gap: 8px;">
        <el-tag type="info" size="small">已选 {{ selectedUsers.length }} 个用户</el-tag>
        <el-button type="success" size="mini" icon="el-icon-check" @click="batchToggle(1)">批量启用</el-button>
        <el-button type="danger" size="mini" icon="el-icon-close" @click="batchToggle(0)">批量禁用</el-button>
        <el-button type="warning" size="mini" icon="el-icon-bank-card" @click="batchRechargeVisible = true">批量充值</el-button>
      </div>

      <!-- 数据表格 -->
      <el-table
        v-loading="loading"
        :data="list"
        stripe
        border
        size="small"
        style="width: 100%"
        :max-height="tableMaxHeight"
        row-key="id"
        @selection-change="handleSelectionChange">
        <el-table-column type="selection" width="45" fixed="left" />
        <el-table-column prop="id" label="ID" width="70" align="center" fixed="left" />
        <el-table-column prop="email" label="邮箱" min-width="180" show-overflow-tooltip />
        <el-table-column prop="invite_code" label="邀请码" width="110" align="center" show-overflow-tooltip />
        <el-table-column prop="inviter_invite_code" label="邀请人码" width="110" align="center" show-overflow-tooltip>
          <template slot-scope="{ row }">
            <span v-if="row.inviter_invite_code">{{ row.inviter_invite_code }}</span>
            <span v-else style="color: #c0c4cc;">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="inviter_id" label="邀请人ID" width="90" align="center">
          <template slot-scope="{ row }">
            <span v-if="row.inviter_id">{{ row.inviter_id }}</span>
            <span v-else style="color: #c0c4cc;">-</span>
          </template>
        </el-table-column>
        <el-table-column label="直推人数" width="90" align="center" prop="team_direct_count">
          <template slot-scope="{ row }">{{ row.team_direct_count != null ? row.team_direct_count : '-' }}</template>
        </el-table-column>
        <el-table-column label="团队业绩" width="110" align="right" prop="team_performance">
          <template slot-scope="{ row }">
            <span class="money-cell">{{ formatMoney(row.team_performance) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="自充点卡" width="110" align="right" sortable prop="point_card_self">
          <template slot-scope="{ row }">
            <span class="money-cell">{{ formatMoney(row.point_card_self) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="赠送点卡" width="110" align="right" sortable prop="point_card_gift">
          <template slot-scope="{ row }">
            <span class="money-cell">{{ formatMoney(row.point_card_gift) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="累计奖励" width="110" align="right" prop="total_reward">
          <template slot-scope="{ row }">
            <span class="money-cell">{{ formatMoney(row.total_reward) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="根用户" width="80" align="center">
          <template slot-scope="{ row }">
            <el-tag v-if="row.is_root" type="danger" size="mini">ROOT</el-tag>
            <span v-else style="color: #c0c4cc;">-</span>
          </template>
        </el-table-column>
        <el-table-column label="等级" width="80" align="center" prop="member_level">
          <template slot-scope="{ row }">
            <el-tag :type="levelTagType(row.member_level)" size="mini">
              {{ levelName(row.member_level) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="80" align="center">
          <template slot-scope="{ row }">
            <el-switch
              v-model="row.status"
              :active-value="1"
              :inactive-value="0"
              @change="handleStatusChange(row)" />
          </template>
        </el-table-column>
        <el-table-column label="注册时间" width="160" align="center" prop="created_at" sortable>
          <template slot-scope="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="260" align="center" fixed="right">
          <template slot-scope="{ row }">
            <el-button type="text" size="small" icon="el-icon-view" @click="openDetail(row)">详情</el-button>
            <el-button type="text" size="small" icon="el-icon-coin" @click="openRecharge(row)">充值</el-button>
            <el-button type="text" size="small" icon="el-icon-present" @click="openGift(row)">赠送</el-button>
            <el-button
              type="text"
              size="small"
              :icon="row.is_market_node ? 'el-icon-circle-close' : 'el-icon-place'"
              @click="toggleMarketNode(row)">
              {{ row.is_market_node ? '取消节点' : '设节点' }}
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="pagination-wrap">
        <el-pagination
          background
          layout="total, sizes, prev, pager, next, jumper"
          :current-page.sync="page"
          :page-size.sync="pageSize"
          :page-sizes="[15, 30, 50, 100]"
          :total="total"
          @size-change="reload"
          @current-change="fetchData" />
      </div>
    </el-card>

    <!-- ========== 用户详情对话框 ========== -->
    <el-dialog
      title="用户详情"
      :visible.sync="detailVisible"
      width="900px"
      :close-on-click-modal="false"
      top="5vh"
      destroy-on-close>
      <div v-loading="detailLoading">
        <template v-if="detailData">
          <!-- 基本信息 -->
          <div class="section-title">基本信息</div>
          <el-descriptions :column="3" border size="small">
            <el-descriptions-item label="用户ID">{{ detailData.id }}</el-descriptions-item>
            <el-descriptions-item label="租户ID">{{ detailData.tenant_id }}</el-descriptions-item>
            <el-descriptions-item label="邮箱">{{ detailData.email }}</el-descriptions-item>
            <el-descriptions-item label="邀请码">{{ detailData.invite_code || '-' }}</el-descriptions-item>
            <el-descriptions-item label="邀请人ID">{{ detailData.inviter_id || '-' }}</el-descriptions-item>
            <el-descriptions-item label="邀请人码">{{ detailData.inviter_invite_code || '-' }}</el-descriptions-item>
            <el-descriptions-item label="邀请人邮箱">{{ detailData.inviter_email || '-' }}</el-descriptions-item>
            <el-descriptions-item label="是否ROOT">
              <el-tag v-if="detailData.is_root" type="danger" size="mini">是</el-tag>
              <span v-else>否</span>
            </el-descriptions-item>
            <el-descriptions-item label="会员等级">
              <el-tag :type="levelTagType(detailData.member_level)" size="mini">
                {{ detailData.level_name || levelName(detailData.member_level) }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="市场节点">
              <el-tag v-if="detailData.is_market_node" type="success" size="mini">是</el-tag>
              <span v-else>否</span>
            </el-descriptions-item>
            <el-descriptions-item label="状态">
              <el-tag :type="detailData.status === 1 ? 'success' : 'info'" size="mini">
                {{ detailData.status === 1 ? '正常' : '禁用' }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="活跃策略">{{ detailData.active_strategies || 0 }}</el-descriptions-item>
            <el-descriptions-item label="注册时间">{{ formatDate(detailData.created_at) }}</el-descriptions-item>
          </el-descriptions>

          <!-- 点卡与奖励 -->
          <div class="section-title" style="margin-top: 20px;">点卡与奖励</div>
          <el-descriptions :column="3" border size="small">
            <el-descriptions-item label="自充点卡">
              <span class="money-value">{{ formatMoney(detailData.point_card_self) }}</span>
            </el-descriptions-item>
            <el-descriptions-item label="赠送点卡">
              <span class="money-value">{{ formatMoney(detailData.point_card_gift) }}</span>
            </el-descriptions-item>
            <el-descriptions-item label="点卡总计">
              <span class="money-value money-total">{{ formatMoney(detailData.point_card_total) }}</span>
            </el-descriptions-item>
            <el-descriptions-item label="奖励余额(USDT)">
              <span class="money-value">{{ formatMoney(detailData.reward_usdt) }}</span>
            </el-descriptions-item>
            <el-descriptions-item label="累计奖励">
              <span class="money-value">{{ formatMoney(detailData.total_reward) }}</span>
            </el-descriptions-item>
            <el-descriptions-item label="已提现">
              <span class="money-value">{{ formatMoney(detailData.withdrawn_reward) }}</span>
            </el-descriptions-item>
          </el-descriptions>

          <!-- 团队信息 -->
          <div class="section-title" style="margin-top: 20px;">团队信息</div>
          <el-descriptions :column="3" border size="small">
            <el-descriptions-item label="直推人数">{{ detailData.team_direct_count || 0 }}</el-descriptions-item>
            <el-descriptions-item label="团队总人数">{{ detailData.team_total_count || 0 }}</el-descriptions-item>
            <el-descriptions-item label="团队业绩">{{ formatMoney(detailData.team_performance) }}</el-descriptions-item>
          </el-descriptions>

          <!-- 直推列表 -->
          <div v-if="detailData.team_direct_count > 0" style="margin-top: 10px;">
            <el-button type="text" icon="el-icon-s-unfold" @click="loadTeam">
              {{ teamList.length ? '刷新直推列表' : '查看直推列表' }}
            </el-button>
            <el-table
              v-if="teamList.length"
              :data="teamList"
              size="mini"
              border
              style="margin-top: 8px;"
              v-loading="teamLoading"
              max-height="250">
              <el-table-column prop="id" label="ID" width="70" align="center" />
              <el-table-column prop="email" label="邮箱" min-width="160" show-overflow-tooltip />
              <el-table-column label="等级" width="80" align="center">
                <template slot-scope="{ row }">
                  <el-tag :type="levelTagType(row.member_level)" size="mini">
                    {{ row.level_name || levelName(row.member_level) }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column label="市场节点" width="80" align="center">
                <template slot-scope="{ row }">
                  <el-tag v-if="row.is_market_node" type="success" size="mini">是</el-tag>
                  <span v-else>-</span>
                </template>
              </el-table-column>
              <el-table-column label="自充点卡" width="100" align="right">
                <template slot-scope="{ row }">{{ formatMoney(row.point_card_self) }}</template>
              </el-table-column>
              <el-table-column label="赠送点卡" width="100" align="right">
                <template slot-scope="{ row }">{{ formatMoney(row.point_card_gift) }}</template>
              </el-table-column>
              <el-table-column label="下级人数" width="80" align="center" prop="sub_count" />
              <el-table-column label="注册时间" width="150" align="center">
                <template slot-scope="{ row }">{{ formatDate(row.created_at) }}</template>
              </el-table-column>
            </el-table>
            <el-pagination
              v-if="teamTotal > teamPageSize"
              small
              layout="prev, pager, next"
              :current-page.sync="teamPage"
              :page-size="teamPageSize"
              :total="teamTotal"
              style="margin-top: 8px; text-align: right;"
              @current-change="loadTeam" />
          </div>

          <!-- 交易所账户 -->
          <div class="section-title" style="margin-top: 20px;">交易所账户</div>
          <el-table
            v-if="detailData.accounts && detailData.accounts.length"
            :data="detailData.accounts"
            size="mini"
            border
            max-height="200">
            <el-table-column prop="id" label="ID" width="60" align="center" />
            <el-table-column label="交易所" width="100">
              <template slot-scope="{ row }">
                <el-tag size="mini">{{ row.exchange }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="账户类型" width="90" align="center" prop="account_type" />
            <el-table-column label="余额" width="120" align="right">
              <template slot-scope="{ row }">{{ formatMoney(row.balance) }}</template>
            </el-table-column>
            <el-table-column label="合约余额" width="120" align="right">
              <template slot-scope="{ row }">{{ formatMoney(row.futures_balance) }}</template>
            </el-table-column>
            <el-table-column label="状态" width="80" align="center">
              <template slot-scope="{ row }">
                <el-tag :type="row.status === 1 ? 'success' : 'info'" size="mini">
                  {{ row.status === 1 ? '正常' : '禁用' }}
                </el-tag>
              </template>
            </el-table-column>
          </el-table>
          <el-empty v-else description="暂无交易所账户" :image-size="60" />

          <!-- 当前持仓 -->
          <div class="section-title" style="margin-top: 20px;">
            <span>当前持仓</span>
            <el-button type="text" size="mini" icon="el-icon-refresh" @click="loadUserPositions" style="margin-left:8px">刷新</el-button>
            <el-button type="text" size="mini" @click="goToPositions" style="margin-left:4px">查看全部 →</el-button>
          </div>
          <el-table
            v-if="userPositions.length"
            :data="userPositions"
            size="mini"
            border
            v-loading="userPosLoading"
            :row-class-name="posPnlRowClass"
            max-height="260">
            <el-table-column label="交易对" width="110">
              <template slot-scope="{ row }">
                <span style="font-weight:600">{{ row.symbol }}</span>
              </template>
            </el-table-column>
            <el-table-column label="交易所" width="80" align="center">
              <template slot-scope="{ row }">
                <el-tag size="mini" effect="plain">{{ (row.exchange || '').toUpperCase() }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="方向" width="60" align="center">
              <template slot-scope="{ row }">
                <el-tag :type="(row.position_side||'').toUpperCase()==='LONG'?'success':'danger'" size="mini" effect="dark">
                  {{ (row.position_side||'').toUpperCase()==='LONG'?'多':'空' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="数量" width="100" align="right">
              <template slot-scope="{ row }">{{ formatNum(row.quantity) }}</template>
            </el-table-column>
            <el-table-column label="均价" width="100" align="right">
              <template slot-scope="{ row }">{{ formatPrice(row.avg_cost) }}</template>
            </el-table-column>
            <el-table-column label="杠杆" width="60" align="center">
              <template slot-scope="{ row }">{{ row.leverage || '-' }}x</template>
            </el-table-column>
            <el-table-column label="未实现盈亏" width="120" align="right">
              <template slot-scope="{ row }">
                <span :style="{color: Number(row.unrealized_pnl)>=0?'#67C23A':'#F56C6C', fontWeight:600}">
                  {{ Number(row.unrealized_pnl)>=0?'+':'' }}{{ formatMoney(row.unrealized_pnl) }}
                </span>
              </template>
            </el-table-column>
            <el-table-column label="状态" width="70" align="center">
              <template slot-scope="{ row }">
                <el-tag :type="row.status==='OPEN'?'success':'info'" size="mini">{{ row.status==='OPEN'?'持仓':'已平' }}</el-tag>
              </template>
            </el-table-column>
          </el-table>
          <el-empty v-if="!userPosLoading && userPositions.length === 0" description="暂无持仓" :image-size="50" />

          <!-- 最近订单 -->
          <div class="section-title" style="margin-top: 20px;">
            <span>最近订单</span>
            <el-button type="text" size="mini" icon="el-icon-refresh" @click="loadUserOrders" style="margin-left:8px">刷新</el-button>
            <el-button type="text" size="mini" @click="goToOrders" style="margin-left:4px">查看全部 →</el-button>
          </div>
          <el-table
            v-if="userOrders.length"
            :data="userOrders"
            size="mini"
            border
            v-loading="userOrderLoading"
            max-height="280">
            <el-table-column label="交易对" width="100">
              <template slot-scope="{ row }">
                <span style="font-weight:600">{{ row.symbol }}</span>
              </template>
            </el-table-column>
            <el-table-column label="交易所" width="80" align="center">
              <template slot-scope="{ row }">
                <el-tag size="mini" effect="plain">{{ (row.exchange || '').toUpperCase() }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="方向" width="70" align="center">
              <template slot-scope="{ row }">
                <el-tag :type="(row.side||'').toUpperCase()==='BUY'?'success':'danger'" size="mini" effect="dark">
                  {{ (row.side||'').toUpperCase()==='BUY'?'买入':'卖出' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="开/平" width="80" align="center">
              <template slot-scope="{ row }">
                <el-tag :type="(row.trade_type||'')==='CLOSE'?'warning':''" size="mini" effect="plain">
                  {{ {OPEN:'开仓',CLOSE:'平仓',ADD:'加仓',REDUCE:'减仓'}[(row.trade_type||'OPEN').toUpperCase()]||'开仓' }}
                </el-tag>
                <div v-if="row.close_reason" style="font-size:10px;margin-top:1px">
                  <el-tag :type="row.close_reason==='TP'?'success':'danger'" size="mini" effect="plain">
                    {{ {SL:'止损',TP:'止盈',SIGNAL:'信号',MANUAL:'手动'}[(row.close_reason||'').toUpperCase()]||row.close_reason }}
                  </el-tag>
                </div>
              </template>
            </el-table-column>
            <el-table-column label="成交" width="110" align="right">
              <template slot-scope="{ row }">
                <span>{{ formatNum(row.filled_quantity) }}</span>
                <span style="color:#C0C4CC"> / {{ formatNum(row.quantity) }}</span>
              </template>
            </el-table-column>
            <el-table-column label="均价" width="100" align="right">
              <template slot-scope="{ row }">{{ formatPrice(row.avg_price) }}</template>
            </el-table-column>
            <el-table-column label="状态" width="80" align="center">
              <template slot-scope="{ row }">
                <el-tag :type="{FILLED:'success',CANCELLED:'info',REJECTED:'danger',PENDING:'warning',PARTIAL:'warning'}[(row.status||'').toUpperCase()]||'info'" size="mini">
                  {{ {FILLED:'已成交',CANCELLED:'已取消',REJECTED:'已拒绝',PENDING:'待处理',PARTIAL:'部分成交'}[(row.status||'').toUpperCase()]||row.status }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="时间" width="145">
              <template slot-scope="{ row }">{{ formatDate(row.created_at) }}</template>
            </el-table-column>
          </el-table>
          <el-empty v-if="!userOrderLoading && userOrders.length === 0" description="暂无订单" :image-size="50" />

          <!-- 奖励记录 -->
          <div class="section-title" style="margin-top: 20px;">奖励记录</div>
          <el-button type="text" icon="el-icon-list" @click="loadRewards">
            {{ rewardList.length ? '刷新奖励记录' : '查看奖励记录' }}
          </el-button>
          <el-table
            v-if="rewardList.length"
            :data="rewardList"
            size="mini"
            border
            style="margin-top: 8px;"
            v-loading="rewardLoading"
            max-height="220">
            <el-table-column prop="reward_type_name" label="类型" width="90" align="center" />
            <el-table-column prop="amount" label="金额(USDT)" width="120" align="right">
              <template slot-scope="{ row }">{{ formatMoney(row.amount) }}</template>
            </el-table-column>
            <el-table-column prop="rate" label="比例" width="80" align="center">
              <template slot-scope="{ row }">{{ row.rate != null ? (row.rate * 100).toFixed(2) + '%' : '-' }}</template>
            </el-table-column>
            <el-table-column prop="source_email" label="来源用户" min-width="140" show-overflow-tooltip />
            <el-table-column prop="remark" label="备注" min-width="100" show-overflow-tooltip />
            <el-table-column prop="created_at" label="时间" width="160" align="center">
              <template slot-scope="{ row }">{{ formatDate(row.created_at) }}</template>
            </el-table-column>
          </el-table>
          <el-pagination
            v-if="rewardTotal > rewardPageSize"
            small
            layout="prev, pager, next, total"
            :current-page.sync="rewardPage"
            :page-size="rewardPageSize"
            :total="rewardTotal"
            style="margin-top: 8px; text-align: right;"
            @current-change="loadRewards" />
          <el-empty v-if="rewardListLoaded && rewardList.length === 0" description="暂无奖励记录" :image-size="50" style="margin-top: 8px;" />
        </template>
      </div>
      <span slot="footer">
        <el-button size="small" @click="detailVisible = false">关闭</el-button>
        <el-button type="primary" size="small" icon="el-icon-coin" @click="openRechargeFromDetail">充值</el-button>
        <el-button type="success" size="small" icon="el-icon-present" @click="openGiftFromDetail">赠送</el-button>
      </span>
    </el-dialog>

    <!-- ========== 充值对话框 ========== -->
    <el-dialog
      title="用户充值"
      :visible.sync="rechargeVisible"
      width="440px"
      :close-on-click-modal="false"
      destroy-on-close>
      <el-form :model="rechargeForm" label-width="100px" size="small">
        <el-form-item label="用户ID">
          <el-input :value="rechargeForm.userId" disabled />
        </el-form-item>
        <el-form-item label="用户邮箱">
          <el-input :value="rechargeForm.email" disabled />
        </el-form-item>
        <el-form-item label="当前自充点卡">
          <el-input :value="formatMoney(rechargeForm.currentSelf)" disabled />
        </el-form-item>
        <el-form-item label="充值金额" required>
          <el-input-number
            v-model="rechargeForm.amount"
            :min="0.01"
            :precision="2"
            :step="10"
            placeholder="请输入金额"
            style="width: 100%" />
        </el-form-item>
      </el-form>
      <span slot="footer">
        <el-button size="small" @click="rechargeVisible = false">取消</el-button>
        <el-button
          type="primary"
          size="small"
          :loading="rechargeLoading"
          @click="submitRecharge">确认充值</el-button>
      </span>
    </el-dialog>

    <!-- ========== 赠送点卡对话框 ========== -->
    <el-dialog
      title="赠送点卡"
      :visible.sync="giftVisible"
      width="440px"
      :close-on-click-modal="false"
      destroy-on-close>
      <el-form :model="giftForm" label-width="100px" size="small">
        <el-form-item label="用户ID">
          <el-input :value="giftForm.userId" disabled />
        </el-form-item>
        <el-form-item label="用户邮箱">
          <el-input :value="giftForm.email" disabled />
        </el-form-item>
        <el-form-item label="当前赠送点卡">
          <el-input :value="formatMoney(giftForm.currentGift)" disabled />
        </el-form-item>
        <el-form-item label="赠送数量" required>
          <el-input-number
            v-model="giftForm.amount"
            :min="0.01"
            :precision="2"
            :step="10"
            placeholder="请输入数量"
            style="width: 100%" />
        </el-form-item>
      </el-form>
      <span slot="footer">
        <el-button size="small" @click="giftVisible = false">取消</el-button>
        <el-button
          type="success"
          size="small"
          :loading="giftLoading"
          @click="submitGift">确认赠送</el-button>
      </span>
    </el-dialog>

    <!-- 批量充值对话框 -->
    <el-dialog title="批量充值" :visible.sync="batchRechargeVisible" width="400px" append-to-body>
      <el-form label-width="90px" size="small">
        <el-form-item label="充值金额">
          <el-input-number v-model="batchRechargeForm.amount" :min="1" :max="100000" style="width:100%;"/>
        </el-form-item>
        <el-form-item label="充值类型">
          <el-radio-group v-model="batchRechargeForm.card_type">
            <el-radio label="self">自充点卡</el-radio>
            <el-radio label="gift">赠送点卡</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item>
          <el-tag type="info" size="small">将为 {{ selectedUsers.length }} 个用户充值</el-tag>
        </el-form-item>
      </el-form>
      <span slot="footer">
        <el-button size="small" @click="batchRechargeVisible = false">取消</el-button>
        <el-button type="primary" size="small" :loading="batchRechargeLoading" @click="submitBatchRecharge">确认充值</el-button>
      </span>
    </el-dialog>
  </div>
</template>

<script>
import {
  getUsers,
  getUserDetail,
  rechargeUser,
  getUserTeam,
  setMarketNode,
  toggleUserStatus,
  getTenants
} from '@/api/admin'
import { getRewards } from '@/api/finance'
import { getPositions, getOrders } from '@/api/trading'
import { batchToggleUsers, batchRechargeUsers } from '@/api/monitor'

const LEVEL_MAP = { 0: '普通', 1: 'V1', 2: 'V2', 3: 'V3', 4: 'V4', 5: 'V5' }

export default {
  name: 'UserManage',
  data() {
    return {
      // ---- 列表 ----
      loading: false,
      list: [],
      total: 0,
      page: 1,
      pageSize: 15,
      where: {
        email: '',
        invite_code: '',
        inviter_id: '',
        point_card_self_min: '',
        point_card_gift_min: '',
        tenant_id: ''
      },

      // ---- 统计 ----
      stats: {
        totalCount: 0,
        todayCount: 0,
        activeCount: 0,
        totalPointCard: 0
      },
      statsLoading: false,

      // ---- 租户下拉 ----
      tenantList: [],

      // ---- 详情 ----
      detailVisible: false,
      detailLoading: false,
      detailData: null,

      // ---- 团队 ----
      teamList: [],
      teamLoading: false,
      teamPage: 1,
      teamPageSize: 10,
      teamTotal: 0,

      // ---- 奖励记录（详情内） ----
      rewardList: [],
      rewardLoading: false,
      rewardListLoaded: false,
      rewardPage: 1,
      rewardPageSize: 10,
      rewardTotal: 0,

      // ---- 用户持仓/订单 ----
      userPositions: [],
      userPosLoading: false,
      userOrders: [],
      userOrderLoading: false,

      // ---- 充值 ----
      rechargeVisible: false,
      rechargeLoading: false,
      rechargeForm: { userId: '', email: '', currentSelf: 0, amount: 0 },

      // ---- 赠送 ----
      giftVisible: false,
      giftLoading: false,
      giftForm: { userId: '', email: '', currentGift: 0, amount: 0 },

      // ---- 批量操作 ----
      selectedUsers: [],
      batchRechargeVisible: false,
      batchRechargeLoading: false,
      batchRechargeForm: { amount: 100, card_type: 'self' },

      // ---- 布局 ----
      tableMaxHeight: 520
    }
  },
  created() {
    this.loadTenants()
    this.fetchData()
    this.loadStats()
  },
  mounted() {
    this.calcTableHeight()
    window.addEventListener('resize', this.calcTableHeight)
  },
  beforeDestroy() {
    window.removeEventListener('resize', this.calcTableHeight)
  },
  methods: {
    // ===================== 表格数据 =====================
    async fetchData() {
      this.loading = true
      try {
        const params = { page: this.page, page_size: this.pageSize }
        if (this.where.email) params.email = this.where.email
        if (this.where.invite_code) params.invite_code = this.where.invite_code
        if (this.where.inviter_id) params.inviter_id = this.where.inviter_id
        if (this.where.point_card_self_min) params.point_card_self_min = this.where.point_card_self_min
        if (this.where.point_card_gift_min) params.point_card_gift_min = this.where.point_card_gift_min
        if (this.where.tenant_id) params.tenant_id = this.where.tenant_id

        const res = await getUsers(params)
        const body = res.data
        if (body.success) {
          this.list = body.data || []
          this.total = body.total || 0
        } else {
          this.$message.error(body.message || '获取用户列表失败')
        }
      } catch (e) {
        this.$message.error('获取用户列表失败')
      } finally {
        this.loading = false
      }
    },
    reload() {
      this.page = 1
      this.fetchData()
      this.loadStats()
    },
    resetSearch() {
      this.where = {
        email: '',
        invite_code: '',
        inviter_id: '',
        point_card_self_min: '',
        point_card_gift_min: '',
        tenant_id: ''
      }
      this.reload()
    },

    // ===================== 统计数据 =====================
    async loadStats() {
      this.statsLoading = true
      try {
        // 拉取全量概要：使用 page_size=1 获取 total，再拉大页做聚合
        const allRes = await getUsers({ page: 1, page_size: 9999 })
        const body = allRes.data
        if (body.success) {
          const allUsers = body.data || []
          const today = new Date().toISOString().slice(0, 10)
          this.stats = {
            totalCount: body.total || allUsers.length,
            todayCount: allUsers.filter(u => (u.created_at || '').slice(0, 10) === today).length,
            activeCount: allUsers.filter(u => u.status === 1).length,
            totalPointCard: allUsers.reduce((s, u) => s + (parseFloat(u.point_card_self) || 0) + (parseFloat(u.point_card_gift) || 0), 0)
          }
        }
      } catch (e) {
        console.warn('加载统计失败', e)
      } finally {
        this.statsLoading = false
      }
    },

    // ===================== 租户下拉 =====================
    async loadTenants() {
      try {
        const res = await getTenants({ page_size: 200 })
        const body = res.data
        if (body.success) {
          this.tenantList = body.data || []
        }
      } catch (e) {
        console.warn('加载租户列表失败', e)
      }
    },

    // ===================== 详情 =====================
    async openDetail(row) {
      this.detailVisible = true
      this.detailLoading = true
      this.detailData = null
      this.teamList = []
      this.teamPage = 1
      this.teamTotal = 0
      this.rewardList = []
      this.rewardListLoaded = false
      this.rewardPage = 1
      this.rewardTotal = 0
      this.userPositions = []
      this.userOrders = []
      try {
        const res = await getUserDetail(row.id)
        const body = res.data
        if (body.success) {
          this.detailData = body.data
          // 并行加载持仓和订单
          this.loadUserPositions()
          this.loadUserOrders()
        } else {
          this.$message.error(body.message || body.detail || '获取详情失败')
        }
      } catch (e) {
        const d = e.response && e.response.data
        const msg = (d && (d.detail || d.message)) || e.message || '获取详情失败'
        this.$message.error(typeof msg === 'string' ? msg : JSON.stringify(msg))
      } finally {
        this.detailLoading = false
      }
    },

    // ===================== 团队 =====================
    async loadTeam() {
      if (!this.detailData) return
      this.teamLoading = true
      try {
        const res = await getUserTeam(this.detailData.id, {
          page: this.teamPage,
          page_size: this.teamPageSize
        })
        const body = res.data
        if (body.success) {
          this.teamList = body.data || []
          this.teamTotal = body.total || 0
        }
      } catch (e) {
        this.$message.error('加载团队数据失败')
      } finally {
        this.teamLoading = false
      }
    },

    // ===================== 奖励记录（详情内） =====================
    async loadRewards() {
      if (!this.detailData) return
      this.rewardLoading = true
      this.rewardListLoaded = true
      try {
        const res = await getRewards({
          user_id: this.detailData.id,
          page: this.rewardPage,
          page_size: this.rewardPageSize
        })
        const body = res.data
        if (body.success) {
          this.rewardList = body.data || []
          this.rewardTotal = body.total || 0
        }
      } catch (e) {
        this.$message.error('加载奖励记录失败')
      } finally {
        this.rewardLoading = false
      }
    },

    // ===================== 用户持仓/订单 =====================
    _getUserAccountIds() {
      if (!this.detailData || !this.detailData.accounts) return []
      return this.detailData.accounts.map(a => a.id)
    },
    async loadUserPositions() {
      const ids = this._getUserAccountIds()
      if (!ids.length) { this.userPositions = []; return }
      this.userPosLoading = true
      try {
        // 逐账户拉取并合并
        const all = []
        for (const aid of ids) {
          const res = await getPositions({ account_id: aid, has_position: true })
          const items = res.data.data || []
          all.push(...items)
        }
        this.userPositions = all.sort((a, b) => new Date(b.updated_at || 0) - new Date(a.updated_at || 0))
      } catch (e) {
        console.warn('加载用户持仓失败', e)
      } finally {
        this.userPosLoading = false
      }
    },
    async loadUserOrders() {
      const ids = this._getUserAccountIds()
      if (!ids.length) { this.userOrders = []; return }
      this.userOrderLoading = true
      try {
        const all = []
        for (const aid of ids) {
          const res = await getOrders({ account_id: aid, limit: 20 })
          const items = res.data.data || []
          all.push(...items)
        }
        // 按时间降序，最多展示20条
        this.userOrders = all
          .sort((a, b) => new Date(b.created_at || 0) - new Date(a.created_at || 0))
          .slice(0, 20)
      } catch (e) {
        console.warn('加载用户订单失败', e)
      } finally {
        this.userOrderLoading = false
      }
    },
    goToPositions() {
      if (!this.detailData) return
      const ids = this._getUserAccountIds()
      if (ids.length) {
        this.$router.push({ path: '/trading/positions', query: { account_id: ids[0] } })
      } else {
        this.$router.push({ path: '/trading/positions' })
      }
    },
    goToOrders() {
      if (!this.detailData) return
      const ids = this._getUserAccountIds()
      if (ids.length) {
        this.$router.push({ path: '/trading/orders', query: { account_id: ids[0] } })
      } else {
        this.$router.push({ path: '/trading/orders' })
      }
    },
    posPnlRowClass({ row }) {
      const pnl = Number(row.unrealized_pnl)
      if (isNaN(pnl)) return ''
      return pnl > 0 ? 'row-profit' : pnl < 0 ? 'row-loss' : ''
    },
    formatNum(val) {
      if (val === null || val === undefined || val === '') return '-'
      const n = Number(val)
      if (isNaN(n)) return val
      return n.toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 6 })
    },
    formatPrice(val) {
      if (val == null || val === '' || val === 0) return '-'
      const n = Number(val)
      if (isNaN(n)) return val
      if (n >= 1000) return n.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
      if (n >= 1) return n.toLocaleString('en-US', { minimumFractionDigits: 4, maximumFractionDigits: 4 })
      return n.toLocaleString('en-US', { minimumFractionDigits: 6, maximumFractionDigits: 8 })
    },

    // ===================== 状态切换 =====================
    async handleStatusChange(row) {
      try {
        await toggleUserStatus(row.id, row.status)
        this.$message.success(`用户 ${row.id} 已${row.status === 1 ? '启用' : '禁用'}`)
      } catch (e) {
        this.$message.error('状态切换失败')
        row.status = row.status === 1 ? 0 : 1  // 回滚
      }
    },

    // ===================== 市场节点 =====================
    async toggleMarketNode(row) {
      const newVal = row.is_market_node ? 0 : 1
      const action = newVal ? '设置为市场节点' : '取消市场节点'
      try {
        await this.$confirm(`确定要将用户 ${row.email} ${action}吗？`, '提示', { type: 'warning' })
      } catch (e) {
        return
      }
      const loading = this.$loading({ lock: true, text: '处理中...' })
      try {
        const res = await setMarketNode(row.id, { is_node: newVal })
        const body = res.data
        if (body.success) {
          this.$message.success(body.message || `${action}成功`)
          row.is_market_node = newVal
        } else {
          this.$message.error(body.message || `${action}失败`)
        }
      } catch (e) {
        this.$message.error(`${action}失败`)
      } finally {
        loading.close()
      }
    },

    // ===================== 充值 =====================
    openRecharge(row) {
      this.rechargeForm = {
        userId: row.id,
        email: row.email,
        currentSelf: row.point_card_self || 0,
        amount: 0
      }
      this.rechargeVisible = true
    },
    openRechargeFromDetail() {
      if (!this.detailData) return
      this.rechargeForm = {
        userId: this.detailData.id,
        email: this.detailData.email,
        currentSelf: this.detailData.point_card_self || 0,
        amount: 0
      }
      this.rechargeVisible = true
    },
    async submitRecharge() {
      if (!this.rechargeForm.amount || this.rechargeForm.amount <= 0) {
        this.$message.warning('请输入有效金额')
        return
      }
      this.rechargeLoading = true
      try {
        const res = await rechargeUser(this.rechargeForm.userId, {
          amount: this.rechargeForm.amount,
          card_type: 'self'
        })
        const body = res.data
        if (body.success) {
          this.$message.success(body.message || '充值成功')
          this.rechargeVisible = false
          this.fetchData()
          this.loadStats()
          // 如果详情对话框打开中，则刷新详情
          if (this.detailVisible && this.detailData && this.detailData.id === this.rechargeForm.userId) {
            this.openDetail({ id: this.rechargeForm.userId })
          }
        } else {
          this.$message.error(body.message || body.detail || '充值失败')
        }
      } catch (e) {
        const msg = (e.response && e.response.data && (e.response.data.detail || e.response.data.message)) || '充值失败'
        this.$message.error(msg)
      } finally {
        this.rechargeLoading = false
      }
    },

    // ===================== 赠送 =====================
    openGift(row) {
      this.giftForm = {
        userId: row.id,
        email: row.email,
        currentGift: row.point_card_gift || 0,
        amount: 0
      }
      this.giftVisible = true
    },
    openGiftFromDetail() {
      if (!this.detailData) return
      this.giftForm = {
        userId: this.detailData.id,
        email: this.detailData.email,
        currentGift: this.detailData.point_card_gift || 0,
        amount: 0
      }
      this.giftVisible = true
    },
    async submitGift() {
      if (!this.giftForm.amount || this.giftForm.amount <= 0) {
        this.$message.warning('请输入有效数量')
        return
      }
      this.giftLoading = true
      try {
        const res = await rechargeUser(this.giftForm.userId, {
          amount: this.giftForm.amount,
          card_type: 'gift'
        })
        const body = res.data
        if (body.success) {
          this.$message.success(body.message || '赠送成功')
          this.giftVisible = false
          this.fetchData()
          this.loadStats()
          if (this.detailVisible && this.detailData && this.detailData.id === this.giftForm.userId) {
            this.openDetail({ id: this.giftForm.userId })
          }
        } else {
          this.$message.error(body.message || body.detail || '赠送失败')
        }
      } catch (e) {
        const msg = (e.response && e.response.data && (e.response.data.detail || e.response.data.message)) || '赠送失败'
        this.$message.error(msg)
      } finally {
        this.giftLoading = false
      }
    },

    // ===================== 工具函数 =====================
    formatMoney(val) {
      const n = parseFloat(val)
      if (isNaN(n)) return '0.00'
      return n.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
    },
    formatDate(val) {
      if (!val) return '-'
      // ISO string -> YYYY-MM-DD HH:mm:ss
      if (typeof val === 'string') {
        return val.replace('T', ' ').slice(0, 19)
      }
      return val
    },
    levelName(lv) {
      return LEVEL_MAP[lv] || ('V' + lv)
    },
    levelTagType(lv) {
      if (!lv || lv === 0) return 'info'
      if (lv >= 4) return 'danger'
      if (lv >= 2) return 'warning'
      return ''
    },
    calcTableHeight() {
      this.$nextTick(() => {
        this.tableMaxHeight = Math.max(300, window.innerHeight - 380)
      })
    },
    // ===================== 批量操作 =====================
    handleSelectionChange(val) {
      this.selectedUsers = val
    },
    async batchToggle(status) {
      const label = status === 1 ? '启用' : '禁用'
      try {
        await this.$confirm(`确认批量${label} ${this.selectedUsers.length} 个用户？`, '批量操作', {type: 'warning'})
      } catch { return }
      try {
        const ids = this.selectedUsers.map(u => u.id)
        const res = await batchToggleUsers({user_ids: ids, status: status})
        this.$message.success((res.data && res.data.message) || '操作成功')
        this.fetchData()
        this.loadStats()
      } catch (e) {
        this.$message.error('批量操作失败')
      }
    },
    async submitBatchRecharge() {
      if (!this.batchRechargeForm.amount || this.batchRechargeForm.amount <= 0) {
        return this.$message.warning('请输入有效金额')
      }
      this.batchRechargeLoading = true
      try {
        const ids = this.selectedUsers.map(u => u.id)
        const res = await batchRechargeUsers({
          user_ids: ids,
          amount: this.batchRechargeForm.amount,
          card_type: this.batchRechargeForm.card_type
        })
        this.$message.success((res.data && res.data.message) || '充值完成')
        this.batchRechargeVisible = false
        this.fetchData()
        this.loadStats()
      } catch (e) {
        this.$message.error('批量充值失败')
      } finally {
        this.batchRechargeLoading = false
      }
    }
  }
}
</script>

<style scoped>
.search-form {
  margin-bottom: 12px;
}
.search-form .el-form-item {
  margin-bottom: 10px;
}
.pagination-wrap {
  display: flex;
  justify-content: flex-end;
  margin-top: 15px;
}
.section-title {
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 10px;
  color: #303133;
  border-left: 3px solid #409eff;
  padding-left: 8px;
}
.money-cell {
  font-family: 'Monaco', 'Menlo', monospace;
  color: #303133;
}
.money-value {
  font-family: 'Monaco', 'Menlo', monospace;
  font-weight: 500;
}
.money-total {
  color: #409eff;
  font-weight: 600;
}
::v-deep .row-profit {
  background-color: rgba(103, 194, 58, 0.04) !important;
}
::v-deep .row-loss {
  background-color: rgba(245, 108, 108, 0.04) !important;
}
</style>
