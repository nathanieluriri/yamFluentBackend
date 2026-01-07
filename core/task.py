 
from controller.session import cleanup_incomplete_session
from repositories.tokens_repo import delete_access_and_refresh_token_with_user_id
from services.session_service import delete_sessions_for_user
from services.coaching_tips_service import delete_coaching_tips_for_user
from repositories.device_state_repo import delete_device_states_for_user



ASYNC_TASK_REGISTRY = {
 
    "delete_tokens":delete_access_and_refresh_token_with_user_id,
    "cleanup_incomplete_session": cleanup_incomplete_session,
    "delete_user_sessions": delete_sessions_for_user,
    "delete_user_coaching_tips": delete_coaching_tips_for_user,
    "delete_user_device_states": delete_device_states_for_user
    
}
