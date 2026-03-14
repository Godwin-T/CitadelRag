from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api.routes.deps import get_current_user, get_db
from api.db import models
from api.schemas.chunk_strategy import ChunkStrategyCreate, ChunkStrategyOut

router = APIRouter(prefix="/chunk-strategies", tags=["chunk-strategies"])


@router.get("", response_model=list[ChunkStrategyOut])
def list_chunk_strategies(db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    strategies = db.query(models.ChunkStrategy).all()
    return [
        ChunkStrategyOut(
            id=s.id,
            name=s.name,
            params_json=s.params_json,
            active=bool(s.active),
        )
        for s in strategies
    ]


@router.post("", response_model=ChunkStrategyOut)
def create_chunk_strategy(
    payload: ChunkStrategyCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    strategy = models.ChunkStrategy(
        name=payload.name,
        params_json=payload.params_json,
        active=payload.active,
    )
    db.add(strategy)
    if payload.active:
        db.query(models.ChunkStrategy).update({models.ChunkStrategy.active: False})
    db.commit()
    db.refresh(strategy)
    return ChunkStrategyOut(
        id=strategy.id,
        name=strategy.name,
        params_json=strategy.params_json,
        active=bool(strategy.active),
    )


@router.post("/{strategy_id}/activate", response_model=ChunkStrategyOut)
def activate_chunk_strategy(
    strategy_id: str,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    strategy = db.query(models.ChunkStrategy).filter(models.ChunkStrategy.id == strategy_id).first()
    if not strategy:
        raise HTTPException(status_code=404, detail="Chunk strategy not found")
    db.query(models.ChunkStrategy).update({models.ChunkStrategy.active: False})
    strategy.active = True
    db.commit()
    db.refresh(strategy)
    return ChunkStrategyOut(
        id=strategy.id,
        name=strategy.name,
        params_json=strategy.params_json,
        active=bool(strategy.active),
    )
