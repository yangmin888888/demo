DEFAULT_ACTOR = (None, "system")


def get_actor(session) -> tuple[int | None, str]:
    """从请求共享的 Session 上取当前操作人。

    说明：FastAPI 的同步依赖/接口运行在不同线程池线程，contextvar 无法跨线程传播，
    因此把操作人绑定到 Session（get_current_user 与业务接口共享同一个探测实例）上。
    """
    return session.info.get("actor", DEFAULT_ACTOR)