package dev.luma.game;

import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class CompanionOwnershipService {
    private static final long LOCAL_PLAYER = 1;
    private final CompanionOwnershipRepository repository;
    public CompanionOwnershipService(CompanionOwnershipRepository repository) { this.repository = repository; }
    @Transactional(readOnly=true)
    public CompanionOwnershipDtos.Ownership owned() {
        // A single SELECT supplies both the roster and active identity from one database snapshot.
        var owned = repository.owned(LOCAL_PLAYER);
        var active = owned.stream().filter(CompanionOwnershipDtos.Owned::active).toList();
        if (active.size()!=1) throw new GameUnavailable("Exactly one active companion required");
        return new CompanionOwnershipDtos.Ownership(owned,active.getFirst().playerCompanionId());
    }
}
