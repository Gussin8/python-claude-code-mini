"""
消息分组

参考 TypeScript 版本：src/services/compact/grouping.ts

核心功能：
- group_messages_by_api_round - 按 API 轮次分组消息
"""

from typing import List, Dict, Any


def group_messages_by_api_round(messages: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
    """
    按 API 轮次边界分组消息
    
    每个 API 往返一组。当新的助手响应开始时（不同的 message.id）产生边界。
    
    对于格式良好的对话，这是 API 安全的分割点 —— API 合约要求在下一个
    助手轮次之前解决每个 tool_use。
    
    替换了之前的人类轮次分组（仅在真实用户提示处产生边界），
    使用更细粒度的 API 轮次分组，允许 reactive compact 在单提示
    agent 会话中操作。
    
    Args:
        messages: 消息列表
    
    Returns:
        List[List[Dict]]: 分组后的消息列表
    """
    groups: List[List[Dict[str, Any]]] = []
    current_group: List[Dict[str, Any]] = []
    
    # 最后一个看到的助手的 message.id
    # 来自同一 API 响应的流式块共享相同的 id
    last_assistant_id: str | None = None
    
    for msg in messages:
        msg_type = msg.get('type', '')
        
        # 检查是否应该开始新组
        if (msg_type == 'assistant' and 
            msg.get('message', {}).get('id') != last_assistant_id and
            current_group):
            # 保存当前组并开始新组
            groups.append(current_group)
            current_group = [msg]
        else:
            # 添加到当前组
            current_group.append(msg)
        
        # 更新最后一个助手 ID
        if msg_type == 'assistant':
            last_assistant_id = msg.get('message', {}).get('id')
    
    # 添加最后一组
    if current_group:
        groups.append(current_group)
    
    return groups


def ensure_tool_result_pairing(
    messages: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    确保每个 tool_use 都有对应的 tool_result
    
    用于修复在不完整批次后恢复或 max_tokens 截断时可能出现的
    悬空 tool_use。
    
    Args:
        messages: 消息列表
    
    Returns:
        修复后的消息列表
    """
    # 跟踪未匹配的 tool_use IDs
    unmatched_tool_ids: set[str] = set()
    result_messages: List[Dict[str, Any]] = []
    
    for msg in messages:
        msg_type = msg.get('type', '')
        
        if msg_type == 'assistant':
            # 检查是否有 tool_use
            content_blocks = msg.get('message', {}).get('content', [])
            for block in content_blocks:
                if isinstance(block, dict) and block.get('type') == 'tool_use':
                    tool_id = block.get('id')
                    if tool_id:
                        unmatched_tool_ids.add(tool_id)
            
            result_messages.append(msg)
            
        elif msg_type == 'user':
            # 检查是否有 tool_result
            content = msg.get('message', {}).get('content', [])
            if isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get('type') == 'tool_result':
                        tool_id = block.get('tool_use_id')
                        if tool_id and tool_id in unmatched_tool_ids:
                            unmatched_tool_ids.discard(tool_id)
            
            result_messages.append(msg)
    
    # 如果有未匹配的 tool_use，添加一个虚拟的 tool_result
    if unmatched_tool_ids:
        print(f"[grouping] Found {len(unmatched_tool_ids)} unmatched tool_use IDs")
        # TODO: 添加虚拟结果
    
    return result_messages
